
import tpgui
from templeplus.playtester import Playtester
from toee import *
from toee import game


class ControllerConsole:
	txt = None
	btn = None
	is_minimized = True
	is_paused = True
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

		# Minimize window
		minimize_btn = tpgui._add_button(ROOT_ID, "btn2")
		minimize_btn.set_text("_"); minimize_btn.x = 0; minimize_btn.y = 0
		minimize_btn.set_style_id("chargen-button")
		minimize_btn.width = 28
		self.minimize_btn = minimize_btn
		def set_wnd_minimized(value):
			self.is_minimized = value
			if self.is_minimized:
				wind.width = 60
				wind.height = 40
				try:
					subw.hide()
				except Exception as e:
					print(str(e))
					pass
				# self.txt.hide()
			else:
				wind.width = 400
				wind.height = 256
				subw.show()
		set_wnd_minimized(True)
		def b2_click():
			if not self.is_minimized: # minimize
				set_wnd_minimized(True)
				minimize_btn.set_text("[[ ]]")
				minimize_btn.width = 28
			else: # maximize
				set_wnd_minimized(False)
				minimize_btn.set_text("_")
				minimize_btn.width = 28
				# self.txt.show()
			return True
		minimize_btn.set_click_handler( b2_click )

		# Pause / Play button
		pause_btn = tpgui._add_button(ROOT_ID, "pause_btn")
		pause_btn.set_text(">>"); pause_btn.x = 40; pause_btn.y = 0
		pause_btn.set_style_id("chargen-button")
		pause_btn.width = 28
		self.pause_btn = pause_btn

		def pause_click():
			def update_text():
				pause_btn.set_text( ">>" if self.is_paused else "||")
				pause_btn.width = 28
				return

			is_paused = not Playtester().get_instance().is_active()
			if is_paused != self.is_paused:
				self.is_paused = is_paused
				update_text()
				return	
			
			if self.is_paused:
				print('clicked to run')
				self.is_paused = False
				update_text()
				Playtester().get_instance().set_active(True)
			else:
				print('clicked to pause')
				self.is_paused = True
				update_text()
				Playtester().get_instance().set_active(False)
			pass
		pause_btn.set_click_handler( pause_click )
