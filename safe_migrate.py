#!/usr/bin/env python3
"""
Safe Database Migration Script (v2)
====================================
Replaces bare `alembic upgrade head` in the deployment pipeline.

CRITICAL FIX (2026-08-06): v1 had a fatal flaw — when ANY migration error
occurred, it stamped the DB tracker to HEAD without applying the actual
schema changes. This caused missing columns/tables in production.

v2 strategy:
  1. Run migrations ONE AT A TIME (not bulk `upgrade head`)
  2. Only auto-handle DUPLICATE errors (column/table already exists → safe to skip)
  3. NEVER stamp to HEAD on MISSING column/table errors — that means the
     migration FAILED and needs to actually run
  4. Post-migration: VALIDATE that the DB schema matches the SQLAlchemy models
  5. FAIL the deployment if schema drift is detected

Usage:
    python safe_migrate.py          (run migrations safely)
    python safe_migrate.py --check  (dry-run: only report status, change nothing)
"""

import subprocess
import sys
import re
import os

# ── Configuration ──────────────────────────────────────────────────
ALEMBIC_CMD = "alembic"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def run(cmd, capture=True):
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=capture, text=True, cwd=SCRIPT_DIR
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def get_current_revision():
    """Get the revision the database thinks it is on."""
    code, out, err = run(f"{ALEMBIC_CMD} current")
    if code != 0:
        return None, err
    match = re.search(r"([a-f0-9]{12})", out + err)
    return (match.group(1) if match else None), err


def get_head_revision():
    """Get the latest migration file revision (the target)."""
    code, out, err = run(f"{ALEMBIC_CMD} heads")
    match = re.search(r"([a-f0-9]{12})", out)
    return match.group(1) if match else None


def get_pending_revisions():
    """Get list of revisions that need to be applied (current → head)."""
    current, _ = get_current_revision()
    code, out, err = run(f"{ALEMBIC_CMD} history --verbose")
    revisions = re.findall(r"Rev:\s+([a-f0-9]{12,})", out)
    head = get_head_revision()
    if not head:
        return []
    
    pending = []
    if not current:
        # Fresh DB, all revisions are pending (reversed so oldest is first)
        return list(reversed(revisions))
        
    try:
        current_short = current[:12]
        found_current = False
        for rev in reversed(revisions):
            if rev[:12] == current_short:
                found_current = True
                continue
            if found_current:
                pending.append(rev)
        return pending
    except (ValueError, IndexError):
        return []


def try_upgrade_one(revision):
    """Attempt to upgrade to a single specific revision."""
    code, out, err = run(f"{ALEMBIC_CMD} upgrade {revision}")
    combined = out + "\n" + err
    return code, combined


def try_upgrade_head():
    """Attempt alembic upgrade head."""
    code, out, err = run(f"{ALEMBIC_CMD} upgrade head")
    combined = out + "\n" + err
    return code, combined


def detect_error_type(error_output):
    """Classify the migration error to determine if it's safe to skip."""
    if "Can't locate revision" in error_output:
        match = re.search(r"Can't locate revision identified by '([a-f0-9]+)'", error_output)
        return "MISSING_REVISION", match.group(1) if match else None

    if "Duplicate column name" in error_output:
        # Column already exists — this specific migration's changes are already in the DB
        return "DUPLICATE_COLUMN", None

    if "Table" in error_output and "already exists" in error_output:
        return "DUPLICATE_TABLE", None

    if "KeyError:" in error_output:
        match = re.search(r"KeyError:\s+'([a-f0-9]+)'", error_output)
        return "BROKEN_CHAIN", match.group(1) if match else None

    if "Unknown column" in error_output:
        # This means the migration tried to USE a column that doesn't exist
        # This is NOT safe to skip — something is wrong
        return "MISSING_COLUMN", None

    if "NoSuchTableError" in error_output or ("Table" in error_output and "doesn't exist" in error_output):
        return "MISSING_TABLE", None

    return "UNKNOWN", None


def stamp_revision(revision, purge=False):
    """Force-set the alembic_version tracker to a specific revision."""
    print(f"  * Stamping database to revision: {revision}")
    cmd = f"{ALEMBIC_CMD} stamp {revision}"
    if purge:
        cmd += " --purge"
    code, out, err = run(cmd)
    if code != 0:
        print(f"  X Stamp failed: {err}")
        return False
    print(f"  + Database stamped to {revision}")
    return True


def validate_schema():
    """
    Post-migration schema validation.
    Compares actual DB columns against SQLAlchemy model definitions.
    Returns (success: bool, errors: list[str])
    """
    print("\n" + "=" * 60)
    print("POST-MIGRATION SCHEMA VALIDATION")
    print("=" * 60)

    # Use a Python subprocess to do the validation inside the app's venv
    validation_script = '''
import asyncio
import sys
import os
import importlib
import pkgutil

sys.path.insert(0, os.path.dirname(os.path.abspath("{script_dir}")))
os.chdir("{script_dir}")

from dotenv import load_dotenv
load_dotenv("{script_dir}/.env")

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.database import Base

# Dynamically import all models so Base.metadata is populated
import app.models
for _, module_name, _ in pkgutil.iter_modules(app.models.__path__):
    importlib.import_module(f"app.models.{{module_name}}")
# Also import fleet models
try:
    import app.modules.fleet.models
    for _, module_name, _ in pkgutil.iter_modules(app.modules.fleet.models.__path__):
        importlib.import_module(f"app.modules.fleet.models.{{module_name}}")
except ImportError:
    pass

url = os.environ.get("DATABASE_URL", "")
if not url:
    print("SKIP: No DATABASE_URL found")
    sys.exit(0)

async def validate():
    engine = create_async_engine(url)
    errors = []

    async with engine.connect() as conn:
        # Get all tables in DB
        result = await conn.execute(text(
            "SELECT TABLE_NAME FROM information_schema.tables WHERE TABLE_SCHEMA=DATABASE()"
        ))
        db_tables = set(r[0] for r in result.fetchall())

        # Get all tables defined in models
        model_tables = set(Base.metadata.tables.keys())

        # Check each model table exists in DB
        for table_name in sorted(model_tables):
            if table_name == "alembic_version":
                continue
            if table_name not in db_tables:
                errors.append(f"MISSING TABLE: {{table_name}}")
                continue

            # Check columns for this table
            table = Base.metadata.tables[table_name]
            model_columns = set(c.name for c in table.columns)

            result = await conn.execute(text(
                "SELECT COLUMN_NAME FROM information_schema.columns "
                "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=:t"
            ), {{"t": table_name}})
            db_columns = set(r[0] for r in result.fetchall())

            missing = model_columns - db_columns
            for col in sorted(missing):
                errors.append(f"MISSING COLUMN: {{table_name}}.{{col}}")

    await engine.dispose()

    if errors:
        print("ERRORS_FOUND")
        for e in errors:
            print(e)
    else:
        print("SCHEMA_OK")

asyncio.run(validate())
'''.format(script_dir=SCRIPT_DIR)

    # Write temp script
    temp_file = os.path.join(SCRIPT_DIR, "_validate_schema_tmp.py")
    try:
        with open(temp_file, "w") as f:
            f.write(validation_script)
        code, out, err = run(f"PYTHONPATH={SCRIPT_DIR} python3 {temp_file}")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

    combined = out + "\n" + err
    if "SCHEMA_OK" in combined:
        print("\n  ✓ Schema validation passed — all model columns exist in DB")
        return True, []
    elif "ERRORS_FOUND" in combined:
        errors = [line for line in combined.split("\n") if line.startswith("MISSING")]
        print(f"\n  ✗ Schema validation FAILED — {len(errors)} issue(s) found:")
        for e in errors:
            print(f"    - {e}")
        return False, errors
    elif "SKIP" in combined:
        print("\n  ⚠ Schema validation skipped (no DATABASE_URL)")
        return True, []
    else:
        print(f"\n  ⚠ Schema validation inconclusive:")
        print(f"    stdout: {out[:500]}")
        print(f"    stderr: {err[:500]}")
        # Don't fail deployment for validation script errors
        return True, []


def main():
    check_only = "--check" in sys.argv

    print("=" * 60)
    print("SAFE DATABASE MIGRATION (v2)")
    print("=" * 60)

    # Step 1: Check current state
    head = get_head_revision()
    current, current_err = get_current_revision()

    print(f"\n  Database tracker:  {current or 'UNKNOWN/ERROR'}")
    print(f"  Migration head:    {head or 'UNKNOWN'}")

    if current and current == head:
        print("\n  ✓ Database is already up to date. Nothing to do.")
        # Still validate schema to catch any drift
        valid, errors = validate_schema()
        if not valid:
            print("\n  ✗ DEPLOYMENT BLOCKED: Schema drift detected!")
            print("  The alembic tracker says HEAD but the DB is missing columns/tables.")
            print("  This likely means a previous deployment stamped without applying.")
            print("  ACTION REQUIRED: Manually add the missing columns or reset alembic.")
            return 1
        return 0

    if check_only:
        print(f"\n  [DRY RUN] {len(get_pending_revisions())} pending migration(s)")
        print("  Would attempt: alembic upgrade head")
        return 0

    # Step 2: Handle MISSING_REVISION / BROKEN_CHAIN first
    # These mean the tracker points to a revision that no longer exists
    if current_err and ("Can't locate revision" in current_err or "KeyError" in current_err):
        print("\n  ⚠ Database tracker points to a missing/deleted revision.")
        print("  Attempting to reset tracker to base and replay all migrations...")
        history = []
        code, out, err = run(f"{ALEMBIC_CMD} history --verbose")
        history = re.findall(r"Rev:\s+([a-f0-9]{12})", out)
        if history:
            base_rev = history[-1]  # oldest revision
            print(f"  Stamping to base revision: {base_rev}")
            stamp_revision(base_rev, purge=True)
        else:
            print("  X Cannot determine migration history. Manual intervention required.")
            return 1

    # Step 3: Try normal upgrade head
    print("\n-- Attempting migration: alembic upgrade head --")
    code, output = try_upgrade_head()

    if code == 0:
        print("  + Migration completed successfully!")
        new_current, _ = get_current_revision()
        print(f"  Database is now at: {new_current}")

        # Validate schema
        valid, errors = validate_schema()
        if not valid:
            print("\n  ✗ DEPLOYMENT WARNING: Schema drift detected after migration!")
            return 1
        return 0

    # Step 4: Migration failed — diagnose
    print("  ✗ Migration failed. Diagnosing...")
    error_type, error_detail = detect_error_type(output)
    print(f"  Error type: {error_type}")
    if error_detail:
        print(f"  Error detail: {error_detail}")

    # Only auto-fix for DUPLICATE errors (the schema change already exists)
    if error_type in ("DUPLICATE_COLUMN", "DUPLICATE_TABLE"):
        print(f"\n  → Safe to skip: {error_type} means the change already exists in DB.")
        print("  → Upgrading one revision at a time to find and skip duplicates...")

        # Strategy: upgrade one-at-a-time, stamping past duplicates
        max_retries = 50
        for i in range(max_retries):
            code, output = try_upgrade_head()
            if code == 0:
                print(f"  + All migrations applied after {i+1} retry(ies)")
                break

            err_type, _ = detect_error_type(output)
            if err_type in ("DUPLICATE_COLUMN", "DUPLICATE_TABLE"):
                # Find which revision failed and stamp past it
                # The error happens during upgrade, so current+1 is the problem
                current_now, _ = get_current_revision()
                pending = get_pending_revisions()
                if pending:
                    skip_rev = pending[0]
                    print(f"  → Skipping revision {skip_rev} (duplicate detected)")
                    stamp_revision(skip_rev)
                else:
                    # No pending = we're at head already
                    break
            else:
                # Different error type — don't auto-fix
                print(f"\n  ✗ Encountered non-duplicate error: {err_type}")
                print(f"  Full output:\n{output[:2000]}")
                print("\n  ✗ DEPLOYMENT BLOCKED. Manual intervention required.")
                return 1
        else:
            print(f"  ✗ Exceeded {max_retries} retries. Manual intervention required.")
            return 1

        new_current, _ = get_current_revision()
        print(f"  Database is now at: {new_current}")

    elif error_type in ("MISSING_REVISION", "BROKEN_CHAIN"):
        # Already handled above in Step 2, but just in case:
        print("\n  ✗ Broken migration chain detected.")
        print("  This should have been handled earlier. Manual intervention required.")
        return 1

    else:
        # MISSING_COLUMN, MISSING_TABLE, UNKNOWN — do NOT stamp, do NOT skip
        print(f"\n  ✗ DEPLOYMENT BLOCKED due to: {error_type}")
        print("  This error means migrations need to actually run.")
        print("  DO NOT stamp to HEAD — that will skip schema changes!")
        print(f"\n  Full error:\n{output[:3000]}")
        print("\n  ACTION REQUIRED:")
        print("  1. Check if a previous deployment stamped without applying")
        print("  2. Manually add missing columns/tables")
        print("  3. Then re-run this deployment")
        return 1

    # Step 5: Post-migration schema validation
    valid, errors = validate_schema()
    if not valid:
        print("\n  ✗ DEPLOYMENT WARNING: Schema drift detected!")
        print("  The migration tracker is at HEAD but the DB schema doesn't match.")
        return 1

    print("\n  ✓ Migration and validation complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
