import asyncio
import sys
import uuid
import logging
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, engine
from app.models.role import Role
from app.models.permission import Permission
from app.models.role_permission import RolePermission

# Fix for asyncio event loop closed error on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed_month_end_permissions():
    """
    Script to grant month-end closing permissions to the required roles.
    - super_admin: gets all month-end closing permissions.
    - franchise: gets month_end_closing:submit and month_end_closing:view.
    """
    async with AsyncSessionLocal() as db:
        # Fetch the roles
        result = await db.execute(select(Role).where(Role.name.in_(["super_admin", "franchise"])))
        roles = result.scalars().all()
        role_map = {role.name: role for role in roles}

        super_admin_role = role_map.get("super_admin")
        franchise_role = role_map.get("franchise")

        if not super_admin_role or not franchise_role:
            logger.error("Roles 'super_admin' or 'franchise' not found!")
            return

        # Define permissions to seed
        permissions_to_seed = [
            ("month_end_closing:submit", "month_end_closing", "submit", "Submit month end closing payments"),
            ("month_end_closing:view", "month_end_closing", "view", "View month end closing records"),
            ("month_end_closing:approve", "month_end_closing", "approve", "Approve month end closing payments")
        ]
        
        perm_map = {}
        for code, module, action, description in permissions_to_seed:
            result = await db.execute(select(Permission).where(Permission.code == code))
            perm = result.scalar_one_or_none()
            if not perm:
                perm = Permission(
                    id=str(uuid.uuid4()),
                    code=code,
                    module=module,
                    action=action,
                    description=description
                )
                db.add(perm)
                logger.info(f"Created missing permission: {code}")
            perm_map[code] = perm
            
        await db.commit() # Commit the new permissions

        # Define which role gets which permission
        role_perm_mapping = {
            "super_admin": [
                "month_end_closing:submit",
                "month_end_closing:view",
                "month_end_closing:approve"
            ],
            "franchise": [
                "month_end_closing:submit",
                "month_end_closing:view"
            ]
        }

        for role_name, perm_list in role_perm_mapping.items():
            role = role_map[role_name]
            for p_code in perm_list:
                perm = perm_map[p_code]
                
                # Check if already exists
                exists = await db.execute(
                    select(RolePermission).where(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == perm.id
                    )
                )
                if not exists.scalar_one_or_none():
                    db.add(RolePermission(
                        id=str(uuid.uuid4()),
                        role_id=role.id,
                        permission_id=perm.id
                    ))
                    logger.info(f"Assigned '{p_code}' to role '{role_name}'")
                else:
                    logger.info(f"Role '{role_name}' already has '{p_code}'")

        await db.commit()
        logger.info("Month-end closing permissions seeded successfully.")
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_month_end_permissions())
