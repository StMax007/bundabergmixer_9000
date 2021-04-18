#pip install kivy
import kivy
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.config import Config
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition, FadeTransition, SlideTransition
from kivy.app import App
from kivy.uix.button import Button
from kivy.properties import (
    NumericProperty, ReferenceListProperty, ObjectProperty
)
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ListProperty
from math import sin, cos, pi
from kivy.clock import mainthread, Clock


import json
from kivy.config import Config

Config.set('kivy', 'keyboard_mode', 'dock')
Config.set('graphics', 'resizable', True)


pump_numbers = 6

global cocktail_configuration_selected
cocktail_configuration_selected = [None] * 4  #[0]: ausgewählte cocktail id; [1]: ausgewaehlte cocktailstärke, [2]: ausgewählte glass größe, [3]: Cocktail-Name

global defined_pin
defined_pin = 1234

global json_data

#<----------------- GPIO-Controlling ---------------------->
def mix_drink():
    global cocktail_configuration_selected
    global json_data
    drink_name = cocktail_configuration_selected[3]

    cocktail_sizes={
                1: 200,
                2: 300,
                3: 350
             }
    glass_size = cocktail_sizes.get(cocktail_configuration_selected[2])

    try:
        for i in range(1, len(json_data['Drinks'][drink_name]) + 1):
            percentage = json_data['Drinks'][drink_name]['Bottle'+str(i)]
            amount = (int(percentage) / 100) * glass_size
            pump_drink(i, amount)
    except:
        print("Drink not found")


def pump_drink(pump_number, milliliter):
    print("Pumpe" + str(pump_number) + " mit " + str(milliliter) + " Milliliter")

#<----------------- Kivy-GUI ---------------------->
# creating the root widget used in .kv file
class BottleSelectionScreen(Screen):
    pass

    def button_pressed(self, text, id):
        global cocktail_configuration_selected
        cocktail_configuration_selected[2] = id
        print(cocktail_configuration_selected)
        self.parent.current = 'submenu3'
        #self.parent.transition.direction = 'left'


    def button_back(self):
        self.parent.current = 'submenu1'
        #self.parent.transition.direction = 'right'

        


class StyleButton(Button):
    pass

class IncreaseAmounButton():
    pass

class MenuScreen(Screen):
    button1 = ObjectProperty(None)
    button2 = ObjectProperty(None)
    button3 = ObjectProperty(None)
    button4 = ObjectProperty(None)
    container = ObjectProperty(None)
    button_left_down = ObjectProperty(None)
    framework_text = ObjectProperty(None)

    screen_site = 0    #Seite auf welcher sich der Bildschrim befindet (Wenn In der Liste hoch oder runter gescrollt wird)

    selecter_settings_drinks_screen = 0
    pass

    def drink_selected(self, text, id):
        if (self.selecter_settings_drinks_screen == 1):
            print("moin")
            self.parent.current = 'pin_input'
        else:
            print(text + " was pressed")
            global cocktail_configuration_selected
            cocktail_configuration_selected[0] = id
            cocktail_configuration_selected[3] = text
            self.parent.current = 'submenu1'
            #self.parent.transition.direction = 'left'

    def next_drinks_up(self):
        number_of_drinks = len( json_data['Drinks'] )
        if (self.screen_site == 0):
            self.screen_site = round(0.49 + (number_of_drinks / 4) )- 1
        else:
            self.screen_site -= 1
        self.update_drink_names()
        print("up")

    def next_drinks_down(self):
        number_of_drinks = len( json_data['Drinks'] )
        if(self.screen_site == (round(0.49 + (number_of_drinks / 4) )- 1) ):
            self.screen_site = 0
        else:
            self.screen_site += 1
        self.update_drink_names()
        print("down")

    def settings(self):
        if (self.selecter_settings_drinks_screen == 1):
            self.parent.current = 'menu'
        else:
            self.parent.current = 'pin_input'
        #self.parent.transition.direction = 'left'

    def configuration_settings_drinks(self):
        self.selecter_settings_drinks_screen = 1
        self.button_left_down.text = "zurück"
        self.framework_text.text = "Einstellungen Getränke"


    def update_drink_names(self):
        global json_data

        cocktail_names = list( json_data['Drinks'].keys() )

        cocktails_number = 4 * self.screen_site
        menu_screens = [self.button1, self.button2, self.button3, self.button4]
        for i in menu_screens:
            i.text = ""
            i.disabled = True

        if((len(cocktail_names)-cocktails_number)> 3):
            cocktails_number_max = 3
        else:
            cocktails_number_max = len(cocktail_names) - cocktails_number - 1
        for i in range(0, cocktails_number_max + 1):
            menu_screens[i].text = cocktail_names[i+cocktails_number]
            menu_screens[i].disabled = False

    def on_pre_enter(self):
        self.update_drink_names()




class AlcoholStrengthScreen(Screen):
    frameworktext = ObjectProperty(None)
    button1 = ObjectProperty(None)
    button2 = ObjectProperty(None)
    button3 = ObjectProperty(None)
    pass

    def button_pressed(self, text, id):
        global cocktail_configuration_selected
        cocktail_configuration_selected[1] = id
        self.parent.current = 'submenu2'
        #self.parent.transition.direction = 'left'

    def button_back(self):
        #self.parent.transition.direction = 'right'
        self.parent.current = 'menu'

    def on_pre_enter(self):
        global cocktail_configuration_selected
        self.frameworktext.text = "Wie willst du dein " + cocktail_configuration_selected[3] + "?"


class ConfirmationScreen(Screen):
    frameworktext = ObjectProperty(None)
    buttonok = ObjectProperty(None)
    cocktail_name = ObjectProperty(None)
    cocktail_size = ObjectProperty(None)
    cocktail_strength = ObjectProperty(None)
    pass

    def button_back(self):
        #self.parent.transition.direction = 'right'
        self.parent.current = 'submenu2'

    def button_ok(self):
        print("los gehts!")
        #self.parent.transition.direction = 'left'
        #self.parent.current = 'submenu4'
        mix_drink()

    def set_selected_cocktail_settings(self):
        global cocktail_configuration_selected
        self.cocktail_name.text = "Ausgewähler Cocktail: "

        if(cocktail_configuration_selected[1] == 1):
            cocktail_strength_chosen = "Mittel"
        elif(cocktail_configuration_selected[1] == 2):
            cocktail_strength_chosen = "Stark"
        else:
            cocktail_strength_chosen = "Wer ist Chuck Norris?!"

        if(cocktail_configuration_selected[2] == 1):
            cocktail_size_chosen = "Mini (200ml)"
        elif(cocktail_configuration_selected[2] == 2):
            cocktail_size_chosen = "Mittel (300ml)"
        else:
            cocktail_size_chosen = "Groß (350ml)"

        self.cocktail_name.text = "Cocktail: " + cocktail_configuration_selected[3]
        self.cocktail_size.text = "Stärke: " + cocktail_strength_chosen
        self.cocktail_strength.text = "Größe: " + cocktail_size_chosen

    def on_pre_enter(self):
        self.set_selected_cocktail_settings()

class FillingScreen(Screen):
    frameworktext = ObjectProperty(None)
    pass

    def update_text(self, text):
        self.frameworktext = text

class SettingsScreen(Screen):
    drinks = ObjectProperty(None)
    cleaning = ObjectProperty(None)
    pin_change = ObjectProperty(None)
    pass

    def button_selected(self, text, id):
        print(text + " was pressed")
        if (id == 1):
            self.parent.current = 'settings_add_drink'

    def back(self):
        self.parent.current = 'menu'

class PinInputScreen(Screen):
    pin_value_input = 0
    pins_inserted = 0
    digit_first = ObjectProperty(None)
    digit_second = ObjectProperty(None)
    digit_third = ObjectProperty(None)
    digit_fourth = ObjectProperty(None)
    pass

    def pin_input(self, number):
        print(number)
        self.pin_value_input = self.pin_value_input*10 + number
        self.pins_inserted = self.pins_inserted + 1
        self.increase_digits()

    def increase_digits(self):
        if self.pins_inserted > 0:
            self.digit_first.background_color = (0, 0, 0, 1)
        else:
            self.digit_first.background_color = (0.42, 0.42, 0.42, 1)
            self.digit_second.background_color = (0.42, 0.42, 0.42, 1)
            self.digit_third.background_color = (0.42, 0.42, 0.42, 1)
            self.digit_fourth.background_color = (0.42, 0.42, 0.42, 1)

        if self.pins_inserted > 1:
            self.digit_second.background_color = (0, 0, 0, 1)
        if self.pins_inserted > 2:
            self.digit_third.background_color = (0, 0, 0, 1)
        if self.pins_inserted > 3:
            self.digit_fourth.background_color = (0, 0, 0, 1)

    def enter(self):
        global defined_pin
        if(self.pin_value_input == defined_pin):
            print("Pin Korrekt")
            self.digit_first.background_color = (1, 1, 1, 1)
            self.digit_second.background_color = (1, 1, 1, 1)
            self.digit_third.background_color = (1, 1, 1, 1)
            self.digit_fourth.background_color = (1, 1, 1, 1)

            self.parent.current = 'settings'
        else:
            print("Pin falsch")
            self.digit_first.background_color = (1,0, 0, 1)
            self.digit_second.background_color = (1,0, 0, 1)
            self.digit_third.background_color = (1,0, 0, 1)
            self.digit_fourth.background_color = (1,0, 0, 1)
        self.pin_value_input = 0
        self.pins_inserted = 0

    def back(self):
        self.parent.current = 'menu'


class SettingsAddScreen(Screen):
    button1 = ObjectProperty(None)
    button2 = ObjectProperty(None)
    button3 = ObjectProperty(None)
    button4 = ObjectProperty(None)
    container = ObjectProperty(None)
    button_left_down = ObjectProperty(None)
    button_right_down = ObjectProperty(None)
    framework_text = ObjectProperty(None)

    screen_site = 0    #Seite auf welcher sich der Bildschrim befindet (Wenn In der Liste hoch oder runter gescrollt wird)

    selecter_settings_drinks_screen = 0
    pass

    def on_pre_enter(self):
        print("on pre enter")
        self.update_drink_names()
        self.button_left_down.text = "zurück"

    def drink_selected(self, text, id):
        print(text + " was pressed")
        global cocktail_configuration_selected
        id = self.screen_site * 4 + id - 1
        cocktail_configuration_selected[0] = id
        cocktail_configuration_selected[3] = text
            
        self.parent.current = 'settings_add_drink_content'
        global application
        application.settings_add_drink_content.initialize(text, 0)
        #self.parent.transition.direction = 'left'

    def next_drinks_up(self):
        number_of_drinks = len( json_data['Drinks'] )
        if (self.screen_site == 0):
            self.screen_site = round(0.49 + (number_of_drinks / 4) )- 1
        else:
            self.screen_site -= 1
        self.update_drink_names()
        print("up")

    def next_drinks_down(self):
        number_of_drinks = len( json_data['Drinks'] )
        if(self.screen_site == (round(0.49 + (number_of_drinks / 4) )- 1) ):
            self.screen_site = 0
        else:
            self.screen_site += 1
        self.update_drink_names()
        print("down")

    def settings(self):
        self.parent.current = 'settings'


    def configuration_settings_drinks(self):
        self.selecter_settings_drinks_screen = 1
        self.button_left_down.text = "zurück"
        self.framework_text.text = "Einstellungen Getränke"


    def update_drink_names(self):
        global json_data

        cocktail_names = list( json_data['Drinks'].keys() )

        cocktails_number = 4 * self.screen_site
        menu_screens = [self.button1, self.button2, self.button3, self.button4]
        for i in menu_screens:
            i.text = ""
            i.disabled = True

        if((len(cocktail_names)-cocktails_number)> 3):
            cocktails_number_max = 3
        else:
            cocktails_number_max = len(cocktail_names) - cocktails_number - 1
        for i in range(0, cocktails_number_max + 1):
            try:
                menu_screens[i].text = cocktail_names[i+cocktails_number]
                menu_screens[i].disabled = False
            except:
                print("Fail")

    def add(self):
        self.parent.current = 'settings_add_drink_content'
        global application
        application.settings_add_drink_content.initialize(0, 1)

        

class SettingsNameContentsScreen(Screen):
    frameworktext = ObjectProperty(None)
    buttonok = ObjectProperty(None)
    buttondelete = ObjectProperty(None)
    cocktail_name = ObjectProperty(None)

    box_1_text = ObjectProperty(None)
    box_1_percentage = ObjectProperty(None)
    box_1_plus = ObjectProperty(None)
    box_1_minus = ObjectProperty(None)

    box_2_text = ObjectProperty(None)
    box_2_percentage = ObjectProperty(None)
    box_2_plus = ObjectProperty(None)
    box_2_minus = ObjectProperty(None)

    button_right = ObjectProperty(None)
    button_left = ObjectProperty(None)

    box_text = 0
    screen_site = 0
    new = 0
    cocktail_name_before = 0

    ventil_percentage = [0] * pump_numbers
    current_pump_selected = 0
    pass


    def on_pre_enter(self):
        global cocktail_configuration_selected
        self.frameworktext.text = "Einstellungen " + cocktail_configuration_selected[3]
        self.frameworktext.color = 1, 1, 1, 1

    def change_digits(self, box_id, sign_id, stop):   #sign_id = 2: plus, sign_id = 1: minus
        if(box_id == 1):
            self.box_text = self.box_1_percentage
        else:
            self.box_text = self.box_2_percentage

        if (sign_id == 1) and (stop == 0):
            self.decrease_digit(0)
            Clock.schedule_interval(self.decrease_digit, 0.1)
        elif (sign_id == 1) and (stop == 1):
            Clock.unschedule(self.decrease_digit, 0.1)
        elif (sign_id == 2) and (stop == 0):
            self.increase_digit(0)
            Clock.schedule_interval(self.increase_digit, 0.1)
        else:
            Clock.unschedule(self.increase_digit, 0.1)


    def decrease_digit(self, dt):
        current_percentage = int(self.box_text.text[:-1])
        if(current_percentage > 0):
            current_percentage -= 1
            self.box_text.text = str(current_percentage) + "%"
        self.ventil_percentage[self.screen_site * 2] = int(self.box_1_percentage.text[:-1])
        self.ventil_percentage[self.screen_site * 2 + 1] = int(self.box_2_percentage.text[:-1])

    def increase_digit(self, dt):
        summe = sum(self.ventil_percentage)
        if(summe < 100):
            current_percentage = int(self.box_text.text[:-1])
            if(current_percentage < 100):
                current_percentage += 1
                self.box_text.text = str(current_percentage) + "%"
            self.ventil_percentage[self.screen_site * 2] = int(self.box_1_percentage.text[:-1])
            self.ventil_percentage[self.screen_site * 2 + 1] = int(self.box_2_percentage.text[:-1])
        

    def button_left_pressed(self):
        global json_data
        number_of_valves = json_data['Valves']
        if (self.screen_site == 0):
            self.screen_site = round(number_of_valves / 2) - 1
        else:
            self.screen_site -= 1
        self.update_valve_names()
        print("left")

    def button_right_pressed(self):
        global json_data
        number_of_valves = json_data['Valves']
        if(self.screen_site == (round(number_of_valves / 2) - 1) ):
            self.screen_site = 0
        else:
            self.screen_site += 1
        self.update_valve_names()
        print("right")


    def update_valve_names(self):
        self.box_1_text.text = "Ventil " + str(self.screen_site * 2 + 1)
        self.box_2_text.text = "Ventil " + str(self.screen_site * 2 + 2)
        self.box_1_percentage.text = str(self.ventil_percentage[self.screen_site * 2]) + "%"
        self.box_2_percentage.text = str(self.ventil_percentage[self.screen_site * 2 + 1]) + "%"

    def button_safe(self):
        summe = sum(self.ventil_percentage)
        if( summe == 100):
            global json_data

            if(self.new == 0):
                json_data['Drinks'].pop(self.cocktail_name_before)

            json_temp = {'Bottle1': 12}
            json_temp.pop('Bottle1')
            for i in range(1, number_of_valves + 1):
                json_temp['Bottle'+str(i)] = self.ventil_percentage[i-1]
            json_data['Drinks'][self.cocktail_name.text] = json_temp
            print(self.cocktail_name.text)
            print("abgeschlossen")
            self.parent.current = "settings_add_drink"
        else:
            self.frameworktext.text = "100% nicht gegeben"
            self.frameworktext.color = 1, 0, 0, 1
            print("100% nicht gegeben")

    def button_delete(self):
        global json_data
        if(self.new == 0):
            json_data['Drinks'].pop(self.cocktail_name_before)
        print("delete")
        self.parent.current = "settings_add_drink"

    def button_back(self):
        self.parent.current = "settings_add_drink"

    def initialize(self, cocktail_name, is_new):
        self.new = is_new
        self.cocktail_name_before = cocktail_name
        global json_data
        number_of_valves = json_data['Valves']
        if( self.new == 1):
            self.buttonok.text = "Hinzufügen"
            self.ventil_percentage = [0] * number_of_valves
            self.cocktail_name.text = "Name"
            self.buttondelete.opacity = 0
        else:
            self.buttonok.text = "Speichern"
            self.ventil_percentage = [0] * number_of_valves
            self.cocktail_name.text = self.cocktail_name_before
            i = 0
            for p in json_data['Drinks'][self.cocktail_name_before]:
                self.ventil_percentage[i] = int( json_data['Drinks'][self.cocktail_name_before][p] ) 
                i = i + 1
            self.buttondelete.opacity = 1
        self.screen_site = 0
        self.update_valve_names()
        self.box_1_percentage.text = str(self.ventil_percentage[0]) + "%"
        self.box_2_percentage.text = str(self.ventil_percentage[1]) + "%"


        
        

class RoundedBox(Widget):
    corners = ListProperty([0, 0, 0, 0])
    line_width = NumericProperty(1)
    resolution = NumericProperty(100)
    points = ListProperty([])

    def compute_points(self, *args):
        self.points = []
        a = - pi

        x = self.x + self.corners[0]
        y = self.y + self.corners[0]
        while a < - pi / 2.:
            a += pi / self.resolution
            self.points.extend([
                x + cos(a) * self.corners[0],
                y + sin(a) * self.corners[0]
                ])

        x = self.right - self.corners[1]
        y = self.y + self.corners[1]
        while a < 0:
            a += pi / self.resolution
            self.points.extend([
                x + cos(a) * self.corners[1],
                y + sin(a) * self.corners[1]
                ])

        x = self.right - self.corners[2]
        y = self.top - self.corners[2]
        while a < pi / 2.:
            a += pi / self.resolution
            self.points.extend([
                x + cos(a) * self.corners[2],
                y + sin(a) * self.corners[2]
                ])

        x = self.x + self.corners[3]
        y = self.top - self.corners[3]
        while a < pi:
            a += pi / self.resolution
            self.points.extend([
                x + cos(a) * self.corners[3],
                y + sin(a) * self.corners[3]
                ])

        self.points.extend(self.points[:2])

class Float_LayoutApp(App):
    menu_screen = 0
    strength_screen = 0
    size_screen = 0
    confirmation_screen = 0
    filling_screen = 0
    settings_screen = 0
    settings_add_drink = 0

    def build(self):
        # Create the screen manager
        self.menu_screen = MenuScreen(name='menu')
        self.strength_screen = AlcoholStrengthScreen(name='submenu1')
        self.size_screen = BottleSelectionScreen(name='submenu2')
        self.confirmation_screen = ConfirmationScreen(name='submenu3')
        self.filling_screen = FillingScreen(name='submenu4')
        self.settings_screen = SettingsScreen(name='settings')
        self.settings_config_drinks = MenuScreen(name='settings_drinks')
        self.settings_config_drinks.configuration_settings_drinks()
        self.pin_input = PinInputScreen(name="pin_input")
        self.settings_add_drink = SettingsAddScreen(name="settings_add_drink")
        self.settings_add_drink_content = SettingsNameContentsScreen(name="settings_add_drink_content")

        sm = ScreenManager(transition=FadeTransition(clearcolor=[0, 0, 0, 1], duration=0.25)) #ScreenManager(transition=SlideTransition())
        sm.add_widget(self.menu_screen)
        sm.add_widget(self.strength_screen)
        sm.add_widget(self.size_screen)
        sm.add_widget(self.confirmation_screen)
        sm.add_widget(self.filling_screen)
        sm.add_widget(self.settings_screen)
        sm.add_widget(self.settings_config_drinks)
        sm.add_widget(self.pin_input)
        sm.add_widget(self.settings_add_drink)
        sm.add_widget(self.settings_add_drink_content)
        

        return sm

    def on_start(self):
        #self.menu_screen.update_drink_names()
        #self.settings_config_drinks.update_drink_names()
        print("start")

global application
# run the app
if __name__ == "__main__":
    global json_data
    with open('cocktail_data.json') as json_file:
        json_data = json.load(json_file)
    global number_of_valves
    number_of_valves = json_data['Valves']
    global application
    application = Float_LayoutApp()
    application.run()

