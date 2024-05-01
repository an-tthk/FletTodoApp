import flet as ft
import mysql.connector

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="<PASSWORD>",
    database="todo"
)

mycursor = mydb.cursor()
mycursor.execute("SELECT * FROM todo")
def main(page: ft.Page):
    page.add(ft.SafeArea(ft.Text("Hello, Flet!")))


ft.app(main)
