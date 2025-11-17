#import flet as ft
#from view.simple_view2 import main

#if __name__ == '__main__':
#    ft.app(target=main)
import flet as ft
from view.simple_view2 import main

if __name__ == "__main__":
    ft.app(target=main, view=ft.WEB_BROWSER)  # abre en navegador