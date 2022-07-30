
import tpgui
from templeplus.playtester import Playtester
from toee import *
from toee import game


class ControllerConsole:
	txt = None
	btn = None
	def __init__(self):
		ROOT_ID = "controller_gui"
		w=tpgui._add_root_container(ROOT_ID, 500,256)
		wind = tpgui._get_container(ROOT_ID)
		wind.x = 10; wind.y = 50
		self.wnd = wind

		# Add background image
		w_img = wind.add_image("art/splash/legal0322_1_1.tga")

		GOAL_STACK_WND_ID = 'goal_stack_wnd'
		tpgui._add_container(ROOT_ID, GOAL_STACK_WND_ID, 500, 200)
		subw = tpgui._get_container(GOAL_STACK_WND_ID)
		print(str(subw))
		subw.y = 38

		# Add title text from mesline
		title_txt = game.get_mesline("mes\\pc_creation.mes", 18013)
		w_txt = subw.add_text(title_txt); w_txt.y = 38; w_txt.x = 0
		w_txt.set_style_by_id("priory-title") # get style from text_styles.json
		#w_txt.style.point_size = 20 # this does not work on predefined fonts
		w_txt.set_text("")
		self.txt = w_txt
		
		# # Add freeform text
		# w_txt2 = wind.add_text("Body text"); w_txt2.y = 20
		# w_txt2.style.point_size = 18


		b = tpgui._add_button(GOAL_STACK_WND_ID, "btn1")
		b.set_text("Goal Stack"); b.x = 0; b.y = 0
		b.set_style_id("chargen-button")
		self.btn = b
		def butclick():
			# b = tpgui._get_button("btn1")
			slot = Playtester.get_instance().__goal_slot__
			scheme = Playtester.get_instance().get_cur_scheme()
			state_txt = "Cur scheme: "
			if scheme is not None:
				state_txt += str(scheme) + " "
			else:
				state_txt += "None "
			
			if slot is not None:
				state_txt += ", Goal Stack:" + str(slot.goal_stack)
			
			self.txt.set_text(state_txt)
			# self.wnd.bring_to_front()
			return True
		b.set_click_handler( butclick )


		b2 = tpgui._add_button(ROOT_ID, "btn2")
		b2.set_text("_"); b2.x = 0; b2.y = 0
		b2.set_style_id("chargen-button")
		b2.width = 28
		self.btn2 = b2
		def b2_click():
			if wind.height > 40:
				wind.height = 40
				wind.width = 60
				b2.set_text("[[ ]]")
				b2.width = 28
				try:
					subw.hide()
				except Exception as e:
					print(str(e))
				# self.txt.hide()
			else:
				b2.set_text("_")
				wind.height = 256
				wind.width = 400
				b2.width = 28
				subw.show()
				# self.txt.show()
			return True
		b2.set_click_handler( b2_click )

