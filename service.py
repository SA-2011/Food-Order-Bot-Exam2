from connection import connection

async def clear_current_fsm(state):
    if await state.get_state() is None:
        return False

    await state.clear()
    return True

async def add_dish_to_cart(tg_id_of_user, dish_id, quantity):
    con = None
    try:
        con = await connection()
        user_id = str(tg_id_of_user)

        async with con.transaction():
            rows = await con.fetch("""
                select item_id, quantity
                from cart_items
                where tg_id_of_user = $1 and dish_id = $2
                order by item_id
                for update
            """, user_id, dish_id)

            if rows:
                total_quantity = sum(row["quantity"] for row in rows) + quantity
                first_item_id = rows[0]["item_id"]
                await con.execute("""
                    update cart_items
                    set quantity = $1,
                        total_price = (select price * $1 from dishes where dish_id = $2)
                    where item_id = $3
                """, total_quantity, dish_id, first_item_id)

                await con.execute("""
                    delete from cart_items
                    where tg_id_of_user = $1 and dish_id = $2 and item_id <> $3
                """, user_id, dish_id, first_item_id)
            else:
                await con.execute("""
                    insert into cart_items (tg_id_of_user, dish_id, quantity, total_price)
                    values ($1, $2, $3,
                            (select price * $3 from dishes where dish_id = $2))
                """, user_id, dish_id, quantity)

        print("Dish added to cart")
        return True
    except Exception as error:
        print(f"Error in adding dish to cart: {error}")
        return False
    finally:
        if con is not None:
            await con.close()

async def get_cart_quantity(tg_id_of_user, dish_id):
    con = None
    try:
        con = await connection()
        return await con.fetchval("""
            select coalesce(sum(quantity), 0)::int
            from cart_items
            where tg_id_of_user = $1 and dish_id = $2
        """, str(tg_id_of_user), dish_id)
    except Exception as error:
        print(f"Error in getting cart quantity: {error}")
        return None
    finally:
        if con is not None:
            await con.close()

async def decrease_dish_in_cart(tg_id_of_user, dish_id):
    con = None
    try:
        con = await connection()
        user_id = str(tg_id_of_user)
        async with con.transaction():
            rows = await con.fetch("""
                select item_id, quantity
                from cart_items
                where tg_id_of_user = $1 and dish_id = $2
                order by item_id
                for update
            """, user_id, dish_id)

            total_quantity = sum(row["quantity"] for row in rows)
            if total_quantity <= 1:
                return total_quantity

            new_quantity = total_quantity - 1
            first_item_id = rows[0]["item_id"]
            await con.execute("""
                update cart_items
                set quantity = $1,
                    total_price = (select price * $1 from dishes where dish_id = $2)
                where item_id = $3
            """, new_quantity, dish_id, first_item_id)
            await con.execute("""
                delete from cart_items
                where tg_id_of_user = $1 and dish_id = $2 and item_id <> $3
            """, user_id, dish_id, first_item_id)
            return new_quantity
    except Exception as error:
        print(f"Error in decreasing cart quantity: {error}")
        return None
    finally:
        if con is not None:
            await con.close()

async def remove_dish_from_cart(tg_id_of_user, dish_id):
    con = None
    try:
        con = await connection()
        status = await con.execute("""
            delete from cart_items
            where tg_id_of_user = $1 and dish_id = $2
        """, str(tg_id_of_user), dish_id)
        return status != "DELETE 0"
    except Exception as error:
        print(f"Error in removing dish from cart: {error}")
        return False
    finally:
        if con is not None:
            await con.close()

async def add_dish_to_menu(is_admin, tg_id_of_author, title, price, description, photo_file_id):
    try:
        con = await connection()
        await con.execute("""
        insert into dishes (is_admin, tg_id_of_author, title, price, description, photo_file_id) values 
        ($1, $2, $3, $4, $5, $6)
        """, is_admin, str(tg_id_of_author), title, price, description, photo_file_id)
        print("Dish added to menu")
    except Exception as error:
        print(f"Error in adding dish to menu: {error}")
    finally:
        await con.close()

async def show_all_dishes():
    try:
        con = await connection()
        rows = await con.fetch("""
        select * from dishes
        """)
        print("Show all dishes OK")
        return rows
    except Exception as error:
        print(f"Error in showing all dishes: {error}")
    finally:
        await con.close()

async def get_dish(dish_id):
    con = None
    try:
        con = await connection()
        return await con.fetchrow(
            "select dish_id, title, price, description, photo_file_id "
            "from dishes where dish_id = $1",
            dish_id,
        )
    except Exception as error:
        print(f"Error in getting dish: {error}")
        return None
    finally:
        if con is not None:
            await con.close()

async def show_cart(tg_id_of_user):
    try:
        con = await connection()
        cart = await con.fetch("""
        select cart_items.tg_id_of_user , dishes.title, dishes.price, cart_items.quantity, cart_items.total_price from cart_items
        join dishes on cart_items.dish_id = dishes.dish_id
        where cart_items.tg_id_of_user = $1
        """, str(tg_id_of_user))
        print("Show cart OK")
        return cart
    except Exception as error:
        print(f"Error in showing cart: {error}")
    finally:
        await con.close()

async def get_cart_stats(tg_id_of_user):
    try:
        con = await connection()
        return await con.fetchrow("""
        select
            sum(quantity) as total_portions,
            count(distinct dish_id) as different_dishes
        from cart_items
        where tg_id_of_user = $1
        """, str(tg_id_of_user))
    except Exception as error:
        print(f"Error in getting cart stats: {error}")
        return None
    finally:
        if con is not None:
            await con.close()

async def clear_cart(tg_id_of_user):
    try:
        con = await connection()
        await con.execute("""
        delete from cart_items where tg_id_of_user = $1
        """, str(tg_id_of_user))
        print("Cart cleared")
    except Exception as error:
        print(f"Error in clearing cart: {error}")
    finally:
        await con.close()

async def is_admin(tg_id_of_user):
    try:
        con = await connection()
        result = await con.fetchrow("""
        select is_admin from dishes where tg_id_of_author = $1
        """, str(tg_id_of_user))
        if result:
            return True
        else:
            return False
    except Exception as error:
        print(f"Error in checking admin status: {error}")
        return False
    finally:
        await con.close()

