import asyncio
import logging
import sys
import uuid

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, engine
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FLEET_PERMISSIONS = [
    ("fleet:drivers:view", "fleet", "drivers:view", "View driver onboarding queue"),
    ("fleet:drivers:approve", "fleet", "drivers:approve", "Approve or reject driver applications"),
]


async def seed_fleet_driver_permissions():
    async with AsyncSessionLocal() as db:
        driver_role = (
            await db.execute(
                select(Role).where(
                    Role.name == "driver",
                    Role.franchise_id.is_(None),
                    Role.warehouse_id.is_(None),
                )
            )
        ).scalar_one_or_none()
        if not driver_role:
            driver_role = Role(id=str(uuid.uuid4()), name="driver")
            db.add(driver_role)
            logger.info("Created global driver role")

        super_admin_role = (
            await db.execute(
                select(Role).where(
                    Role.name == "super_admin",
                    Role.franchise_id.is_(None),
                    Role.warehouse_id.is_(None),
                )
            )
        ).scalar_one_or_none()
        if not super_admin_role:
            logger.error("Global super_admin role not found")
            return

        perm_map = {}
        for code, module, action, description in FLEET_PERMISSIONS:
            result = await db.execute(select(Permission).where(Permission.code == code))
            perm = result.scalar_one_or_none()
            if not perm:
                perm = Permission(
                    id=str(uuid.uuid4()),
                    code=code,
                    module=module,
                    action=action,
                    description=description,
                )
                db.add(perm)
                logger.info("Created permission %s", code)
            perm_map[code] = perm

        await db.commit()

        for code in perm_map:
            perm = perm_map[code]
            exists = await db.execute(
                select(RolePermission).where(
                    RolePermission.role_id == super_admin_role.id,
                    RolePermission.permission_id == perm.id,
                )
            )
            if not exists.scalar_one_or_none():
                db.add(
                    RolePermission(
                        id=str(uuid.uuid4()),
                        role_id=super_admin_role.id,
                        permission_id=perm.id,
                    )
                )
                logger.info("Assigned %s to super_admin", code)

        await db.commit()
        logger.info("Fleet driver permissions seeded successfully")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_fleet_driver_permissions())
