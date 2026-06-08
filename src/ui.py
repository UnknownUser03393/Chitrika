import flet as ft


def main(page: ft.Page):
	page.title = "我的第一个 Flet 应用"
	page.vertical_alignment = ft.MainAxisAlignment.CENTER
	page.horizontal_alignment = ft.CrossAxisAlignment.CENTER  # 添加水平居中

	# 用于显示数字的文本控件
	input = ft.TextField(value="0", text_align=ft.TextAlign.RIGHT, width=100)

	# 定义按钮的点击事件
	def minus_click(e):
		input.value = str(int(input.value) - 1)
		page.update()

	def plus_click(e):
		input.value = str(int(input.value) + 1)
		page.update()

	page.add(
		ft.Row(
			alignment=ft.MainAxisAlignment.CENTER,
			controls=[
				ft.IconButton(ft.icons.Icons.REMOVE_CIRCLE_OUTLINED, on_click=minus_click),
				input,
				ft.IconButton(ft.icons.Icons.ADD_CIRCLE_OUTLINED, on_click=plus_click),
			],
		)
	)

	# 可选：添加一些使用提示
	page.add(
		ft.Text("点击按钮加减数字", italic=True, size=12, color=ft.Colors.GREY_600)
	)


ft.app(main)