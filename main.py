#pip install kivy
from os import terminal_size
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
import sched, time
from functools import partial

#!<-------- Raspberry-Pi specific ------------->!
try:
    import RPi.GPIO as GPIO
except:
    print("cant import GPIO")

def GPIO_init():
    try:
        GPIO.setmode(GPIO.BOARD)
        
        GPIO_pump = [29, 31, 33, 35, 37, 40] #definieren der GPIOs, an welchen die Pumpen angeschlossen sind
        [GPIO.setup(i,GPIO.OUT) for i in GPIO_pump] 
        [GPIO.output(i,False) for i in GPIO_pump]
    except:
        print("cant Init GPIOs")

#!<-------------------------------------------->!

from kivy.config import Config

Config.set('kivy', 'keyboard_mode', 'dock')
Config.set('graphics', 'resizable', True)



global cocktail_configuration_selected
cocktail_configuration_selected = [None] * 4  #[0]: ausgewählte cocktail id; [1]: ausgewaehlte cocktailstärke, [2]: ausgewählte glass größe, [3]: Cocktail-Name

global backub_pin
backub_pin = 44332211

global json_data

global number_of_valves
number_of_valves = 6

global abort_drink
abort_drink = 0 # ist 1, wenn beim abfüllen des Getränks auf Abbrechen gedrückt wird

def shutdown():
    global number_of_valves
    print("shutdown")
    [pump_adc(i, 0) for i in range(1, number_of_valves + 1)]
    from subprocess import call
    call("sudo nohup shutdown -h now", shell=True)

def safe_json():
    #code zum speichern der Json-Datei
    global json_data
    with open('cocktail_data.json', 'w') as outfile:
        json.dump(json_data, outfile)
    print("json safed 873265")

#<----------------- GPIO-Controlling ---------------------->
def mix_drink():
    global cocktail_configuration_selected
    global json_data, number_of_valves
    drink_name = cocktail_configuration_selected[3]

    cocktail_sizes={
                1: 200,
                2: 300,
                3: 350
             }
    alcohol_factors = {
        1: 1,
        2: 1.5,
        3: 2
    }
    glass_size = cocktail_sizes.get(cocktail_configuration_selected[2])
    alcohol_factor = alcohol_factors.get(cocktail_configuration_selected[1])

    amount = list()
    try:
        valve_names = json_data['Valves']['ValveConfig'].keys()
        is_alcohol = [ json_data['Valves']['ValveConfig'][i]['Alcohol'] for i in valve_names]    #checken in welchen Ventilen Alkohol ist, um die Stärke anzupassen

        for i in range(1, number_of_valves + 1):
            percentage = json_data['Drinks'][drink_name]['Bottle'+str(i)]
            volume = (int(percentage) / 100) * glass_size
            if(is_alcohol[i-1]):
                volume = volume * alcohol_factor
            amount.append([volume, i] )   #2-Diemsnionale Liste bestehen aus der Menge am Anfang und der Pumpennummer anschließend
            pump_drink(i, amount[-1])
            #if(amount[-1][0] > 0):                 #hier werden alle benötigten Pumpen aktiviert
            #    pump_adc(i-1, 1)

        for i in range(0, number_of_valves):# Die Milliliter, die aus den Getränken fliesen werden aus der json_config pro Getränk raus gerechnet, um dem Benutzer anzuzeigen wenn die Flasche leer ist
            json_data['Valves']['ValveConfig'][ list( valve_names )[i] ]['Volume'] = json_data['Valves']['ValveConfig'][ list( valve_names )[i] ]['Volume'] - int( amount[i][0] )
        safe_json()
        
        time_start = list()

        for i in range(0, len(amount)):
            if( amount[i][0] > 0):
                time_start.append( [0, 1, amount[i][1] ])
            else:
                time_start.append( [ 0, 0, amount[i][1] ] )

        time_last_pump = time.time() - 2
        Clock.schedule_once(partial(pump_drink_adc, amount, time_start, time_last_pump), 0.5)
        
        # s = sched.scheduler(time.time, time.sleep)
        # s.enter(0.5, 1, pump_drink_adc, argument=(amount,time_start, s))  #alle 10 Sekunden wurd pump_drink_adc ausgeführt
        # s.run()
        #pump_drink_adc(amount)
    except:
        print("Drink not found")


def pump_drink(pump_number, milliliter):
    print("Pumpe" + str(pump_number) + " mit " + str(milliliter) + " Milliliter")

def pump_drink_adc(amount, time_start, time_last_pump, test):     #hier wird überprüft ob eine Pumpe ausgeschaltet werden muss
    global abort_drink, number_of_valves
    if(abort_drink == 0):
        # Ventile einschalten
        if( ( time.time() - time_last_pump) > 2 ):
            for i in time_start:
                if( (i[0] == 0) & (i[1] == 1) ):    #i[0] = Zeit zu der das Ventil eingeschalten wurde --> war es bisher noch aus steht 0 drinnen. i[1] = 1 wenn das ventil benutzt wird (mehr als 0ml Fluss), ansonsten 0
                    i[0] = time.time()
                    pump_adc(i[2], 1)       #i[2] = Ventil-Nummer
                    time_last_pump = time.time()    # 2ter Timer, der sicherstellt dass nur alle 2 Sekunde ein Ventil eingeschaltet wird 
                    break
        
        #Ventile auschalten
        for i in range(0, number_of_valves):
            if( (time_start[i][0] != 0) & (time_start[i][1] == 1) ):        # checkt, ob aus dem Ventil überhaupt Flüssigkeit fliesen soll
                time_diff = time.time() - time_start[i][0]
                ventil_factor = 30/500   #Faktor, der aus einer Zeit die Amount of Milliliter errechnet --> muss mit den Ventilen erarbeitet werden wie groß der Faktor ist; hier: in 30 Sekunden fließt 500ml
                amount_flowed = time_diff / ventil_factor
                amount_extracted = amount[i][0]

                if( amount_extracted <= amount_flowed ):
                    ventil_nummer = time_start[i][2]
                    pump_adc(ventil_nummer, 0)
                    time_start[i][1] = 0

        still_flowing = 0       #0, wenn kein Ventil mehr aktiv ist, ansonten 1
        for i in time_start:
            if( i[1] == 1 ):
                still_flowing = 1
                break
        if (still_flowing == 1): 
            Clock.schedule_once(partial(pump_drink_adc, amount, time_start, time_last_pump), 0.5)

        else:
            global application
            application.filling_screen.filled_succesfull(1)
    return 1

def pump_adc(pump_number, on_off):
    print("Ventil: " + str(pump_number) + " Zustand: " + str(on_off))   
    try:
        GPIO_pump = [29, 31, 33, 35, 37, 40] #definieren der GPIOs, an welchen die Pumpen angeschlossen sind
        if(on_off == 1):
            try:
                GPIO.output(GPIO_pump[pump_number-1], True)
            except:
                print("on")
        else:
            try:
                GPIO.output(GPIO_pump[pump_number-1],False)
            except:
                print("off")
    except:
        print("Fehler")
    

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
            print("go to setting")
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
        self.frameworktext.text = "    Wie willst du dein " + cocktail_configuration_selected[3] + "?"


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
        mix_drink()
        self.parent.current = 'submenu4'

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
    abort = ObjectProperty(None)
    image = ObjectProperty(None)
    filled_is_finished = 0
    abort = 0   #ist 1, wenn auf Abbrechen gedrückt wurde
    pass

    def button_abort(self):
        global abort_drink, number_of_valves
        if(abort_drink == 0):   #Der Button darf nur einmal gedrückt werden, wird er zweimal oder öfters gedrückt, so kann ein Fehler durch den Clock.schedule_once-Aufruf geschehen
            abort_drink = 1
            [pump_adc(i, 0) for i in range(1, number_of_valves + 1)]
            self.frameworktext.text = "Abbruch"
            Clock.schedule_once(partial(self.back_to_home), 2)  #durch aktive Interrupts (alle 0.5 Sekunden) kann es passieren, dass ein Getränk wieder eingeschaltet wird. Daher muss hier für 2 Sekunden abort_drink auf 1 bleiben
            print("Abbrechen")

    def abort_second_time(self):
        [pump_adc(i, 0) for i in range(1, number_of_valves + 1)]
        global abort_drink
        abort_drink = 0
        self.back_to_home()
    
    def filled_succesfull(self, status):
        self.filled_is_finished = status

    def filled_finished(self, example):
        if(self.filled_is_finished == 1):
            self.image.source = 'cheers.gif'
            self.frameworktext.text = "Cheers!"
            self.filled_is_finished = 0
            self.abort.opacity = 0
            Clock.schedule_once(partial(self.back_to_home), 10)
        else:
            Clock.schedule_once(partial(self.filled_finished), 1)

    def back_to_home(self, example):
        #!! Abfrage ob Flasche leer hinzufügen
        global json_data
        valve_names = json_data['Valves']['ValveConfig'].keys()
        volume_left = [ json_data['Valves']['ValveConfig'][i]['Volume'] for i in valve_names]    #checken in welchen Ventilen Alkohol ist, um die Stärke anzupassen

        if( min( volume_left) < 100):    #wenn unter 100 Milliliter in einem Gefäß sind
            print("Attention: One Bottle may be empty")
            self.parent.current = 'attention_bottle_empty_screen'
        else:
            self.parent.current = 'menu'

    def on_pre_enter(self):
        global cocktail_configuration_selected, abort_drink
        abort_drink = 0
        self.frameworktext.text = cocktail_configuration_selected[3] + " wird zubereitet"
        self.image.source = 'party_hard.jpg'
        self.abort.opacity = 1
        Clock.schedule_once(partial(self.filled_finished), 1)




class SettingsScreen(Screen):
    drinks = ObjectProperty(None)
    cleaning = ObjectProperty(None)
    pin_change = ObjectProperty(None)
    pass

    def button_selected(self, text, id):
        print(text + " was pressed")
        if (id == 1):
            self.parent.current = 'settings_add_drink'

        if (id == 2):
            self.parent.current = 'settings_ventil_screen'

        if (id == 3):
            self.parent.current = 'settings_change_pin'

        if (id == 4):
            self.parent.current = 'settings_clean'

    def button_shutdown(self):
        shutdown()
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
        global json_data, backub_pin
        json_pin = int( json_data['Pin'] )
        if( (self.pin_value_input == json_pin) or (self.pin_value_input == backub_pin) ):
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

    def on_pre_enter(self):
        self.pin_value_input = 0
        self.pins_inserted = 0
        self.digit_first.background_color = (0.42, 0.42, 0.42, 1)
        self.digit_second.background_color = (0.42, 0.42, 0.42, 1)
        self.digit_third.background_color = (0.42, 0.42, 0.42, 1)
        self.digit_fourth.background_color = (0.42, 0.42, 0.42, 1)

class PinChangeScreen(Screen):
    pin_value_input = 0
    pins_inserted = 0
    digit_first = ObjectProperty(None)
    digit_second = ObjectProperty(None)
    digit_third = ObjectProperty(None)
    digit_fourth = ObjectProperty(None)
    pass

    def pin_input(self, number):
        print(number)
        if self.pins_inserted < 4:
            self.pin_value_input = self.pin_value_input*10 + number
            self.pins_inserted = self.pins_inserted + 1
            self.increase_digits()

    def increase_digits(self):
        if self.pins_inserted > 0:
            self.digit_first.text = str( int( self.pin_value_input / (10**(self.pins_inserted-1) ) % 10) )
        else:
            self.digit_first.text = ''
            self.digit_second.text = ''
            self.digit_third.text = ''
            self.digit_fourth.text = ''

        if self.pins_inserted > 1:
            self.digit_second.text = str( int( self.pin_value_input / (10**(self.pins_inserted-2) ) % 10) )
        if self.pins_inserted > 2:
            self.digit_third.text = str( int( self.pin_value_input / (10**(self.pins_inserted-3) ) % 10) )
        if self.pins_inserted > 3:
            self.digit_fourth.text = str( int( self.pin_value_input / (10**(self.pins_inserted-4) ) % 10) )

    def enter(self):
        global json_data
        json_data['Pin'] = int( self.pin_value_input )

        safe_json()

        print("Neuer Pin: " + str( self.pin_value_input ) )


        self.parent.current = 'settings'


    def back(self):
        self.parent.current = 'settings'

    def on_pre_enter(self):
        self.digit_first.text = ''
        self.digit_second.text = ''
        self.digit_third.text = ''
        self.digit_fourth.text = ''
        self.pin_value_input = 0
        self.pins_inserted = 0


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
        self.button_left_down.text = "zurück & speichern"

    def drink_selected(self, text, id):
        print(text + " was pressed")
        global cocktail_configuration_selected
        id = self.screen_site * 4 + id - 1
        cocktail_configuration_selected[0] = id
        cocktail_configuration_selected[3] = text
        
        global application
        application.settings_add_drink_content.initialize(text, 0)
        self.parent.current = 'settings_add_drink_content'
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
        global application
        application.settings_add_drink_content.initialize(0, 1)
        self.parent.current = 'settings_add_drink_content'

        

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
    
    global number_of_valves
    ventil_percentage = [0] * number_of_valves
    current_pump_selected = 0
    pass


    def on_pre_enter(self):
        global cocktail_configuration_selected
        if( self.new == 1):
            self.frameworktext.text = "Einstellungen neues Getränk"
        else:
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
        global json_data, number_of_valves
        if (self.screen_site == 0):
            self.screen_site = round(number_of_valves / 2) - 1
        else:
            self.screen_site -= 1
        self.update_valve_names()
        print("left")

    def button_right_pressed(self):
        global json_data, number_of_valves
        if(self.screen_site == (round(number_of_valves / 2) - 1) ):
            self.screen_site = 0
        else:
            self.screen_site += 1
        self.update_valve_names()
        print("right")


    def update_valve_names(self):
        global json_data
        valve_names = json_data['Valves']['ValveConfig'].keys()
        bottle_names = list()
        [bottle_names.append( json_data['Valves']['ValveConfig'][i]['Name'] ) for i in valve_names]

        self.box_1_text.text = bottle_names[ self.screen_site * 2 ]
        self.box_2_text.text = bottle_names[ self.screen_site * 2 + 1 ]
        self.box_1_percentage.text = str(self.ventil_percentage[self.screen_site * 2]) + "%"
        self.box_2_percentage.text = str(self.ventil_percentage[self.screen_site * 2 + 1]) + "%"

    def button_safe(self):
        global json_data, number_of_valves

        summe = sum(self.ventil_percentage)
        unique_name = 1 #wird ein neuer Cocktail angelegt, ist die Frage ob der Name neu ist, asonsten würde ein bereits vorhandener Cocktail überschrieben

        if (self.new != 0):
            if( self.cocktail_name.text in json_data['Drinks'].keys() ):
                unique_name = 0

        if( summe != 100 ):
            self.frameworktext.text = "100% nicht gegeben"
            self.frameworktext.color = 1, 0, 0, 1
            print("100% nicht gegeben")
        elif( unique_name == 0 ):
            self.frameworktext.text = "Name schon vorhanden"
            self.frameworktext.color = 1, 0, 0, 1
            print("Name schon vorhanden")
        else:

            json_temp = {'Bottle1': 12}
            json_temp.pop('Bottle1')
            for i in range(1, number_of_valves + 1):
                json_temp['Bottle'+str(i)] = self.ventil_percentage[i-1]
            
            if(self.new == 0):
                json_data['Drinks'] = collections.OrderedDict([(self.cocktail_name.text, v) if k == self.cocktail_name_before else (k, v) for k, v in json_data['Drinks'].items()])
            
            json_data['Drinks'][self.cocktail_name.text] = json_temp
            
            print(self.cocktail_name.text)

            safe_json()
            print("abgeschlossen")
            self.parent.current = "settings_add_drink"

    def button_delete(self):
        global json_data
        if(self.new == 0):
            json_data['Drinks'].pop(self.cocktail_name_before)
            safe_json()
        print("delete")
        self.parent.current = "settings_add_drink"

    def button_back(self):
        self.parent.current = "settings_add_drink"

    def initialize(self, cocktail_name, is_new):
        global number_of_valves
        self.new = is_new
        self.cocktail_name_before = cocktail_name
        global json_data
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


#!<--------- Screen zum einstellen der Getränke ----------->!#
class SettingsVentilScreen(Screen):     
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

    def bottle_selected(self, text, id):
        print(text + " was pressed")
        valve_selected = self.screen_site * 4 + id
        print("test")
        global application
        application.settings_ventil_content.valve_selected = valve_selected
        self.parent.current = "settings_ventil_content_screen"


    def next_drinks_up(self):
        global number_of_valves
        number_of_drinks = number_of_valves
        if (self.screen_site == 0):
            self.screen_site = round(0.49 + (number_of_drinks / 4) )- 1
        else:
            self.screen_site -= 1
        self.update_drink_names()
        print("up")

    def next_drinks_down(self):
        global number_of_valves
        number_of_drinks = number_of_valves
        if(self.screen_site == (round(0.49 + (number_of_drinks / 4) )- 1) ):
            self.screen_site = 0
        else:
            self.screen_site += 1
        self.update_drink_names()
        print("down")

    def back(self):
        self.parent.current = 'settings'
        #self.parent.transition.direction = 'left'




    def update_drink_names(self):
        global json_data, number_of_valves

        valve_names = json_data['Valves']['ValveConfig'].keys()
        bottle_names = list()
        [bottle_names.append( json_data['Valves']['ValveConfig'][i]['Name'] ) for i in valve_names]


        ventil_names = ['Ventil 1', 'Ventil 2', 'Ventil 3', 'Ventil 4', 'Ventil 5', 'Ventil 6' ]
        
        cocktail_names = list()
        [cocktail_names.append( ventil_names[i] + "\n" + bottle_names[i]) for i in range(0, number_of_valves)]

        volume_left = [ json_data['Valves']['ValveConfig'][i]['Volume'] for i in valve_names]    #checken in welchen Ventilen wie viel Liter ist, um die Flaschen mit wenig Inhalt rot anzuzeigen

        cocktails_number = 4 * self.screen_site
        menu_screens = [self.button1, self.button2, self.button3, self.button4]
        for i in menu_screens:
            i.text = ""
            i.disabled = True
            i.background_color = (1, 1, 1, 1)

        if((len(cocktail_names)-cocktails_number)> 3):
            cocktails_number_max = 3
        else:
            cocktails_number_max = len(cocktail_names) - cocktails_number - 1
        for i in range(0, cocktails_number_max + 1):
            menu_screens[i].text = cocktail_names[i+cocktails_number]
            menu_screens[i].disabled = False
            
            if( volume_left[i+cocktails_number] < 100):            #ist unter 100 Milliliter im Getränk ist der Hintergrund rot, ansonsten grün
                menu_screens[i].background_color = (1, 0.31, 0, 1)
            else:
                menu_screens[i].background_color = (0, 0.81, 0, 1)

    def on_pre_enter(self):
        self.update_drink_names()


class SettingsVentilContent(Screen):
    frameworktext = ObjectProperty(None)
    buttonok = ObjectProperty(None)
    cocktail_name = ObjectProperty(None)
    is_alcoholic = ObjectProperty(None)
    box_1_text = ObjectProperty(None)
    box_1_plus = ObjectProperty(None)
    box_1_minus = ObjectProperty(None)

    box_text = 0
    valve_selected = 0
    content_ml = 0

    pass


    def on_pre_enter(self):
        self.frameworktext.text = "Einstellungen Ventil" + str(self.valve_selected)
        self.frameworktext.color = 1, 1, 1, 1
        global json_data
        self.box_1_text.text = str( json_data['Valves']['ValveConfig']['Valve'+str(self.valve_selected)]['Volume'] ) + 'ml'
        self.cocktail_name.text = json_data['Valves']['ValveConfig']['Valve'+str(self.valve_selected)]['Name']

        if( json_data['Valves']['ValveConfig']['Valve'+str(self.valve_selected)]['Alcohol'] == 1):
            self.is_alcoholic.state = 'down'
        else:
            self.is_alcoholic.state = 'normal'

    def change_digits(self, sign_id, stop):   #sign_id = 2: plus, sign_id = 1: minus
        self.box_text = self.box_1_text
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
        current_percentage = int(self.box_text.text[:-2])
        if(current_percentage > 0):
            if( (current_percentage  % 50) == 0):
                current_percentage -= 50
            else:
                current_percentage  -= current_percentage  % 50
            self.box_text.text = str(current_percentage) + "ml"
        self.content_ml = current_percentage

    def increase_digit(self, dt):
        current_percentage = int(self.box_text.text[:-2])
        current_percentage += 50 - (current_percentage % 50)
        self.box_text.text = str(current_percentage) + "ml"
        self.content_ml = current_percentage


    def button_safe(self):
        print("safe")
        global json_data

        unique_name = 1 #wird ein neuer Cocktail angelegt, ist die Frage ob der Name neu ist, asonsten würde ein bereits vorhandener Cocktail überschrieben

        valve_names = json_data['Valves']['ValveConfig'].keys()
        bottle_names = list()
        [bottle_names.append( json_data['Valves']['ValveConfig'][i]['Name'] ) for i in valve_names]
        bottle_names.remove( json_data['Valves']['ValveConfig']['Valve' + str(self.valve_selected)]['Name'] )
        if( self.cocktail_name.text in bottle_names ):
            unique_name = 0

        if( unique_name == 0 ):
            self.frameworktext.text = "Name schon vorhanden"
            self.frameworktext.color = 1, 0, 0, 1
            print("Name schon vorhanden")
        else:
            json_data['Valves']['ValveConfig']['Valve' + str(self.valve_selected)]['Name'] = self.cocktail_name.text
            json_data['Valves']['ValveConfig']['Valve' + str(self.valve_selected)]['Volume'] = int( self.box_1_text.text[:-2] )
            if( self.is_alcoholic.state == 'down'):
                json_data['Valves']['ValveConfig']['Valve'+str(self.valve_selected)]['Alcohol'] = 1
            else:
                json_data['Valves']['ValveConfig']['Valve'+str(self.valve_selected)]['Alcohol'] = 0
            
            
            print(self.cocktail_name.text)

            safe_json()

            print("abgeschlossen")
            self.parent.current = "settings_ventil_screen"


    def button_back(self):
        self.parent.current = "settings_ventil_screen"

    

#!<--------- Screen zum einstellen der Getränke Ende ----------->!#

class SettingsCleanScreen(Screen):
    drinks = ObjectProperty(None)
    cleaning = ObjectProperty(None)
    pass

    def button_selected(self, text, id):
        print(text + " was pressed")
        if (id == 1):
            self.parent.current = 'settings_chose_ventil'

        if (id == 2):
            self.parent.current = 'settings_empty_all_bottle'

    def back(self):
        self.parent.current = 'settings'

class SelectVentilScreen(Screen):     
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
        print(text + " was pressed")
        ventil_selected = [int(s) for s in text.split() if s.isdigit()][0]  #Ventil Nummer aus text extrahieren
        global application
        application.setting_empty_bottle.ventil_number = ventil_selected
        self.parent.current = 'setting_empty_bottle'


    def next_drinks_up(self):
        global number_of_valves
        number_of_drinks = number_of_valves
        if (self.screen_site == 0):
            self.screen_site = round(0.49 + (number_of_drinks / 4) )- 1
        else:
            self.screen_site -= 1
        self.update_drink_names()
        print("up")

    def next_drinks_down(self):
        global number_of_valves
        number_of_drinks = number_of_valves
        if(self.screen_site == (round(0.49 + (number_of_drinks / 4) )- 1) ):
            self.screen_site = 0
        else:
            self.screen_site += 1
        self.update_drink_names()
        print("down")

    def back(self):
        self.parent.current = 'settings_clean'
        #self.parent.transition.direction = 'left'




    def update_drink_names(self):
        global json_data, number_of_valves

        cocktail_names = ["Ventil " + str(i) for i in range(1, number_of_valves + 1)]

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


class EmptyBottleScreen(Screen):
    frameworktext = ObjectProperty(None)
    buttonok = ObjectProperty(None)
    ventil_number = 0
    on_off = 0
    pass

    def button_back(self):
        self.on_off = 0
        self.set_pump()
        self.parent.current = 'settings_chose_ventil'

    def button_ok(self):
        print("ventil gedrückt")
        if(self.on_off == 0):
            self.on_off = 1
            self.buttonok.text = "Ventil " + str(self.ventil_number) + " schließen"
            self.buttonok.background_color = (1, 0.31, 0, 1)
        else:
            self.on_off = 0
            self.buttonok.text = "Ventil " + str(self.ventil_number) + " öffnen"
            self.buttonok.background_color = (0, 0.81, 0, 1)
        self.set_pump()
    
    def set_pump(self):
        pump_adc(self.ventil_number, self.on_off)

    def on_pre_enter(self):
        if(self.on_off == 0):
            self.buttonok.text = "Ventil " + str(self.ventil_number) + " öffnen"
            self.buttonok.background_color = (0, 0.81, 0, 1)
        else:
            self.buttonok.text = "Ventil " + str(self.ventil_number) + " schließen"
            self.buttonok.background_color = (1, 0.31, 0, 1)

class EmptyAllBottleScreen(Screen):
    frameworktext = ObjectProperty(None)
    buttonok = ObjectProperty(None)
    on_off = 0
    pass

    def button_back(self):
        #self.parent.transition.direction = 'right'
        self.on_off = 0
        self.set_pumps()
        self.parent.current = 'settings_clean'

    def button_ok(self):
        print("ventil gedrückt")
        if(self.on_off == 0):
            self.on_off = 1
            self.buttonok.text = "Ventile schließen"
            self.buttonok.background_color = (1, 0.31, 0, 1)
        else:
            self.on_off = 0
            self.buttonok.text = "Ventile öffnen"
            self.buttonok.background_color = (0, 0.81, 0, 1)
        self.set_pumps()

    def set_pumps(self):
        global number_of_valves
        [pump_adc(i, self.on_off) for i in range(1, number_of_valves + 1)]

    def on_pre_enter(self):
        if(self.on_off == 0):
            self.buttonok.text = "Ventile öffnen"
        else:
            self.buttonok.text = "Ventile schließen"

class AttentionBottleEmpty(Screen):
    frameworktext = ObjectProperty(None)
    buttonok = ObjectProperty(None)
    cocktail_name = ObjectProperty(None)
    text = ObjectProperty(None)

    box_text = 0
    valve_selected = 1
    content_ml = 0

    pass


    def on_pre_enter(self):
        self.frameworktext.text = "Achtung, eine Flasche ist bald leer!"
        self.frameworktext.color = 1, 1, 1, 1

        global json_data, number_of_valves
        valve_names = json_data['Valves']['ValveConfig'].keys()
        bottle_names = [ json_data['Valves']['ValveConfig'][i]['Name'] for i in valve_names] 
        volume_left = [ json_data['Valves']['ValveConfig'][i]['Volume'] for i in valve_names] 
        text_ouput = ""
        for i in range(0, number_of_valves):
            text_ouput = text_ouput + bottle_names[i] + ":    " + str( volume_left[i] ) + "ml\n"
        self.volume_text.text = text_ouput
        

    def button_ok(self):
        self.parent.current = "menu"

    


class Float_LayoutApp(App):
    menu_screen = 0
    strength_screen = 0
    size_screen = 0
    confirmation_screen = 0
    filling_screen = 0
    settings_screen = 0
    settings_add_drink = 0
    pin_change = 0
    settings_clean = 0
    setting_empty_bottle = 0
    settings_empty_all_bottle = 0
    settings_ventil = 0

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
        self.pin_change = PinChangeScreen(name='settings_change_pin')
        self.settings_clean = SettingsCleanScreen(name='settings_clean')
        self.settings_clean_ventil = SelectVentilScreen(name='settings_chose_ventil')
        self.setting_empty_bottle = EmptyBottleScreen(name='setting_empty_bottle')
        self.settings_empty_all_bottle = EmptyAllBottleScreen(name='settings_empty_all_bottle')
        self.settings_ventil = SettingsVentilScreen(name='settings_ventil_screen')
        self.settings_ventil_content = SettingsVentilContent(name='settings_ventil_content_screen')
        self.attention_bottle_empty = AttentionBottleEmpty(name='attention_bottle_empty_screen')

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
        sm.add_widget(self.pin_change)
        sm.add_widget(self.settings_clean)
        sm.add_widget(self.setting_empty_bottle)
        sm.add_widget(self.settings_empty_all_bottle)
        sm.add_widget(self.settings_clean_ventil)
        sm.add_widget(self.settings_ventil)
        sm.add_widget(self.settings_ventil_content)
        sm.add_widget(self.attention_bottle_empty)
        

        return sm

    def on_start(self):
        #self.menu_screen.update_drink_names()
        #self.settings_config_drinks.update_drink_names()
        print("start")

# run the app
if __name__ == "__main__":
    global json_data
    with open('cocktail_data.json') as json_file:
        json_data = json.load(json_file)

    import collections
    json_data = collections.OrderedDict(json_data)

    number_of_valves = json_data['Valves']['number_of']

    GPIO_init()
    global application
    application = Float_LayoutApp()
    application.run()

