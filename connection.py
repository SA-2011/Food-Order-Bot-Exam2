import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def connection():
    try:
        con = await asyncpg.connect(
            database="finall_exam_fro_bot",
            host="localhost",
            user="postgres",
            port=5432,
            password=os.getenv("da_password")
        )
        print("Connection OK")
        return con
    except Exception as error:
        print(f"Error in connection: {error}")

async def create_table():
    try:
        con = await connection()
        await con.execute("""
        create table if not exists dishes (
            dish_id serial primary key,
            tg_id_of_author varchar,
            title text,
            price int,
            description text,
            photo_file_id text not null,
            is_admin boolean default false
        );

        create table if not exists cart_items (
            item_id serial primary key,
            tg_id_of_user varchar,
            dish_id int references dishes(dish_id) on delete cascade,
            quantity int check (quantity > 0),
            total_price int
        );
        """)
        print("Create table OK")
    except Exception as error:
        print(f"Error in creating table: {error}")
    finally:
        await con.close()