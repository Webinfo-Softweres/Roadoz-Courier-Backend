import re

def patch_file():
    with open("app/services/order_service.py", "r") as f:
        content = f.read()

    # 1. search_pickup_addresses
    search_pickup_orig = """    franchise_id = await _resolve_franchise_id(db, current_user)
    is_global = not current_user.franchise_id and not await _get_franchise_for_user(db, current_user.id) and not await _get_warehouse_for_user(db, current_user.id)
    
    query = select(PickupAddress)
    count_query = select(func.count()).select_from(PickupAddress)
    
    if not is_global:
        if franchise_id:
            query = query.where(PickupAddress.franchise_id == franchise_id)
            count_query = count_query.where(PickupAddress.franchise_id == franchise_id)
        else:
            query = query.where(PickupAddress.user_id == current_user.id)
            count_query = count_query.where(PickupAddress.user_id == current_user.id)"""
            
    search_pickup_new = """    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)
    is_global = (franchise_id is None and warehouse_id is None)
    
    query = select(PickupAddress)
    count_query = select(func.count()).select_from(PickupAddress)
    
    if not is_global:
        if franchise_id:
            query = query.where(PickupAddress.franchise_id == franchise_id)
            count_query = count_query.where(PickupAddress.franchise_id == franchise_id)
        elif warehouse_id:
            query = query.where(PickupAddress.warehouse_id == warehouse_id)
            count_query = count_query.where(PickupAddress.warehouse_id == warehouse_id)
        else:
            query = query.where(PickupAddress.user_id == current_user.id)
            count_query = count_query.where(PickupAddress.user_id == current_user.id)"""
            
    content = content.replace(search_pickup_orig, search_pickup_new)

    # 2. create_pickup_address
    create_pickup_orig = """    franchise_id = await _resolve_franchise_id(db, current_user)

    address_str = f"{data.address_line_1}, {data.city}, {data.state} {data.pincode}, {data.country}"
    coords = await get_coordinates_from_address(address_str)

    addr = PickupAddress(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        franchise_id=franchise_id,"""
        
    create_pickup_new = """    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    address_str = f"{data.address_line_1}, {data.city}, {data.state} {data.pincode}, {data.country}"
    coords = await get_coordinates_from_address(address_str)

    addr = PickupAddress(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        franchise_id=franchise_id,
        warehouse_id=warehouse_id,"""
        
    content = content.replace(create_pickup_orig, create_pickup_new)
    
    # 3. update_pickup_address
    update_pickup_orig = """    franchise_id = await _resolve_franchise_id(db, current_user)
    if franchise_id and addr.franchise_id != franchise_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif not franchise_id and addr.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")"""
        
    update_pickup_new = """    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)
    is_global = (franchise_id is None and warehouse_id is None)
    
    if not is_global:
        if franchise_id and addr.franchise_id != franchise_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if warehouse_id and addr.warehouse_id != warehouse_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if not franchise_id and not warehouse_id and addr.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")"""

    content = content.replace(update_pickup_orig, update_pickup_new)
    
    # 4. delete_pickup_address (lines are similar to update)
    # The exact same replace logic should work, because the code block is identical.
    
    
    # 5. search_consignees
    search_consignee_orig = """    franchise_id = await _resolve_franchise_id(db, current_user)
    is_global = not current_user.franchise_id and not await _get_franchise_for_user(db, current_user.id) and not await _get_warehouse_for_user(db, current_user.id)

    query = select(Consignee)
    count_query = select(func.count()).select_from(Consignee)

    if not is_global:
        if franchise_id:
            query = query.where(Consignee.franchise_id == franchise_id)
            count_query = count_query.where(Consignee.franchise_id == franchise_id)
        else:
            query = query.where(Consignee.user_id == current_user.id)
            count_query = count_query.where(Consignee.user_id == current_user.id)"""
            
    search_consignee_new = """    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)
    is_global = (franchise_id is None and warehouse_id is None)

    query = select(Consignee)
    count_query = select(func.count()).select_from(Consignee)

    if not is_global:
        if franchise_id:
            query = query.where(Consignee.franchise_id == franchise_id)
            count_query = count_query.where(Consignee.franchise_id == franchise_id)
        elif warehouse_id:
            query = query.where(Consignee.warehouse_id == warehouse_id)
            count_query = count_query.where(Consignee.warehouse_id == warehouse_id)
        else:
            query = query.where(Consignee.user_id == current_user.id)
            count_query = count_query.where(Consignee.user_id == current_user.id)"""
            
    content = content.replace(search_consignee_orig, search_consignee_new)
    
    # 6. create_consignee
    create_consignee_orig = """    franchise_id = await _resolve_franchise_id(db, current_user)

    address_str = f"{data.address_line_1}, {data.city}, {data.state} {data.pincode}"
    coords = await get_coordinates_from_address(address_str)

    consignee = Consignee(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        franchise_id=franchise_id,"""
        
    create_consignee_new = """    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)

    address_str = f"{data.address_line_1}, {data.city}, {data.state} {data.pincode}"
    coords = await get_coordinates_from_address(address_str)

    consignee = Consignee(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        franchise_id=franchise_id,
        warehouse_id=warehouse_id,"""
        
    content = content.replace(create_consignee_orig, create_consignee_new)
    
    # 7. update_consignee
    update_consignee_orig = """    franchise_id = await _resolve_franchise_id(db, current_user)
    if franchise_id and csg.franchise_id != franchise_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif not franchise_id and csg.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")"""
        
    update_consignee_new = """    franchise_id = await _resolve_franchise_id(db, current_user)
    warehouse_id = await _resolve_warehouse_id(db, current_user)
    is_global = (franchise_id is None and warehouse_id is None)
    
    if not is_global:
        if franchise_id and csg.franchise_id != franchise_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if warehouse_id and csg.warehouse_id != warehouse_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if not franchise_id and not warehouse_id and csg.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")"""

    content = content.replace(update_consignee_orig, update_consignee_new)
    
    # 8. delete_consignee
    # Exact same logic as update_consignee

    with open("app/services/order_service.py", "w") as f:
        f.write(content)

if __name__ == "__main__":
    patch_file()
