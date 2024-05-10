import os
import flet as ft
import MySQLdb
from dotenv import load_dotenv, dotenv_values
from flet.auth.providers import GoogleOAuthProvider
from user_controls.Task import Task

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
assert DB_HOST, "set DB_HOST environment variable"
DB_USER = os.getenv("DB_USER")
assert DB_USER, "set DB_USER environment variable"
DB_PASSWD = os.getenv("DB_PASSWD")
assert DB_PASSWD, "set DB_PASSWD environment variable"
DB_DATABASE = os.getenv("DB_DATABASE")
assert DB_DATABASE, "set DB_DATABASE environment variable"

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
assert GOOGLE_CLIENT_ID, "set GOOGLE_CLIENT_ID environment variable"
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
assert GOOGLE_CLIENT_SECRET, "set GOOGLE_CLIENT_SECRET environment variable"
GOOGLE_TOKEN_REDIRECT_URI = os.getenv("GOOGLE_TOKEN_REDIRECT_URI")
assert GOOGLE_TOKEN_REDIRECT_URI, "set GOOGLE_TOKEN_REDIRECT_URI environment variable"

class C:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class DB:
    exited = False
    conn = None

    def __init__(self):
        self.connect()

    def __del__(self):
        exited = True
        self.conn.close()

    def connect(self):
        if self.exited is True:
            return None

        while self.conn is None:
            try:
                self.conn = MySQLdb.connect(
                    host=DB_HOST,
                    user=DB_USER,
                    passwd=DB_PASSWD,
                    database=DB_DATABASE,
                    charset="utf8"
                )
            except Exception as e:
                pass

        self.conn.autocommit(True)
        self.conn.ping(True)

    def cursor(self):
        try:
            return self.conn.cursor() if self.exited is not True else None
        except (AttributeError, MySQLdb.OperationalError) as e:
            self.connect()
            return self.cursor()

    def close(self):
        del self


db = DB()
cur = db.cursor()


def main(page: ft.Page):
    global db
    global cur

    provider = GoogleOAuthProvider(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        redirect_url=GOOGLE_TOKEN_REDIRECT_URI,
    )

    async def add_clicked(e):
        if new_task.value:
            task = Task(new_task.value, task_status_change, task_delete)
            tasks.controls.append(task)
            new_task.value = ""
            new_task.focus()
            await update_async()

    async def task_status_change(task):
        await update_async()

    async def task_delete(task):
        tasks.controls.remove(task)
        cur.execute("DELETE FROM todo  WHERE id = %s", (task.task_id,))
        await update_async()

    async def tabs_changed(e):
        await update_async()

    async def clear_clicked(e):
        for task in tasks.controls[:]:
            if task.completed:
                await task_delete(task)

    async def update_async():
        status = task_filter.tabs[task_filter.selected_index].text
        user_id = await page.client_storage.get_async('userid')
        count = 0

        for task in tasks.controls:
            task.visible = (
                    status == "all"
                    or (status == "active" and task.completed is False)
                    or (status == "completed" and task.completed)
            )

            if not task.completed:
                count += 1
                completed_num = 0
            else:
                completed_num = 1

            # save task to db, and create if not exists
            if task.task_id == -1:
                cur.execute("INSERT INTO todo (userid, field, completed, datetime) VALUES (%s, %s, %s, NOW())",
                            (user_id, task.task_name, completed_num))
                task.task_id = cur.lastrowid
            else:
                cur.execute("UPDATE todo SET field = %s, completed = %s WHERE id = %s",
                            (task.task_name, completed_num, task.task_id))

        items_left.value = f"{count} active item(s) left"
        page.update()

    def on_login(e: ft.LoginEvent):
        if e.error:
            raise Exception(e.error)

        tasks.controls.clear()
        page.client_storage.clear()

        cur.execute("SELECT id FROM users WHERE username='%s'" % page.auth.user["email"])
        result = cur.fetchall()

        if len(result) == 0:
            cur.execute("INSERT INTO users (username) VALUES (%s)",
                        (page.auth.user["email"],))
            user_id = cur.lastrowid
        else:
            user_id = result[0][0]

        #print(f"{result} {len(result)} {user_id}")

        cur.execute("SELECT id, field, completed FROM todo WHERE userid='%s'" % user_id)
        result = cur.fetchall()

        for row in result:
            task = Task(row[1], task_status_change, task_delete, row[2] == 1, row[0])
            count = 0
            if not task.completed:
                count += 1
            items_left.value = f"{count} active item(s) left"
            tasks.controls.append(task)

        page.client_storage.set('user', page.auth.user["email"])
        page.client_storage.set('userid', user_id)
        logged_user.value = page.client_storage.get('user')
        toggle_login_buttons()
        page.update()

    def logout_button_click(e):
        page.client_storage.remove('user')
        page.client_storage.remove('userid')
        page.logout()

    def on_logout(e):
        toggle_login_buttons()
        page.update()

    def toggle_login_buttons():
        login_button.visible = page.auth is None
        logged_user.visible = logout_button.visible = todo_content.visible = page.auth is not None
        if page.client_storage.get('user') is None:
            logged_user.value = ""

    logged_user = ft.Text(style=ft.TextThemeStyle.BODY_SMALL)

    new_task = ft.TextField(
        hint_text="What needs to be done?", on_submit=add_clicked, expand=True
    )

    tasks = ft.Column()

    task_filter = ft.Tabs(
        scrollable=False,
        selected_index=0,
        on_change=tabs_changed,
        tabs=[ft.Tab(text="all"), ft.Tab(text="active"), ft.Tab(text="completed")],
    )

    items_left = ft.Text("0 items left")

    login_button = ft.ElevatedButton("Login", on_click=lambda _: page.login(provider))
    logout_button = ft.ElevatedButton("Logout", on_click=logout_button_click)

    todo_content = ft.Column(
        width=600,
        controls=[
            ft.Row(
                controls=[
                    new_task,
                    ft.FloatingActionButton(
                        icon=ft.icons.ADD, on_click=add_clicked
                    ),
                ],
            ),
            ft.Column(
                spacing=25,
                controls=[
                    task_filter,
                    tasks,
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            items_left,
                            ft.OutlinedButton(
                                text="Clear completed", on_click=clear_clicked
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )

    page.on_login = on_login
    page.on_logout = on_logout

    toggle_login_buttons()

    page.add(
        ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text(
                                    value=f"Todos",
                                    style=ft.TextThemeStyle.HEADLINE_MEDIUM
                                ),
                                logged_user,
                                ft.Row([login_button, logout_button])
                            ]
                        )
                    ],
                ),
                todo_content
            ]
        )
    )
    page.update()


if __name__ == "__main__":
    try:
        ft.app(target=main, port=8080, view=ft.WEB_BROWSER)
    except KeyboardInterrupt:
        print('\n' + C.OKBLUE + 'Interrupted by the user.' + C.ENDC)
        db.close()
    except MySQLdb.Error as e:
        try:
            print('[' + C.ERROR + 'Error' + C.ENDC + '] database error [%d]: %s' % (e.args[0], e.args[1]))
        except IndexError:
            print('[' + C.ERROR + 'Error' + C.ENDC + '] database error : %s' % (str(e)))
    finally:
        exit(1)
