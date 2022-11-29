# This files contains your custom actions which can be used to run
# custom Python code.

from typing import Any, Text, Dict, List
from datetime import datetime, timedelta
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import ReminderScheduled
import mysql.connector as mysql

DBUSERNAME = "chatbot"
DBPW = "chatbotDB"
DBADDRESS = "35.232.172.36"
DBNAME = "h_farm"

class DBConnectionHandler():

    def connect(self):

        connection = mysql.connect(host = DBADDRESS, user = DBUSERNAME, password = DBPW, database = DBNAME)
        
        return connection

    def closeConnection(self, connection):

        connection.commit()
        connection.close()

        return

class ActionGetCoursesList(Action):

    def name(self) -> Text:
        return "action_get_courses_list"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        userFirstname = "user"
        userEmail = "user@mail.com"

        connection = DBConnectionHandler.connect(self)
        cursor = connection.cursor()

        cursor.execute ("SELECT shortname FROM mdl_course")  #TODO da completare
	    
        userInfo = cursor.fetchall()

        DBConnectionHandler.closeConnection(self, connection)
        
        buttons=[]
        for i in userInfo:
            tuple_to_str = "".join(i)
            fill_slot = '{"course" : "' + tuple_to_str + '"}'
            buttons.append({"title": tuple_to_str, "payload" : f'/course_selected{fill_slot}'})
        
        dispatcher.utter_message(text = "Che corsi vorresti seguire?", buttons = buttons)

        return []


#TODO action per lessons_list


class ActionGetCourseInfo(Action):

     def name(self) -> Text:
        return "action_get_course_info"

     def run(self, dispatcher: CollectingDispatcher,
             tracker: Tracker,
             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text= 'info del corso ' + tracker.get_slot('course')) #TODO info da estrarre da db, creare buttons con title = nome corso da DB

        return []

class ActionGetLink(Action):

     def name(self) -> Text:
        return "action_get_link"

     def run(self, dispatcher: CollectingDispatcher,
             tracker: Tracker,
             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

            connection = DBConnectionHandler.connect(self)

            cursor = connection.cursor(buffered = True)

            courseName = tracker.get_slot('course')

            cursor.execute ("SELECT externalurl FROM mdl_url WHERE mdl_url.course = (SELECT id FROM mdl_course WHERE shortname = %s)", (courseName, ))
            
            course_link = cursor.fetchone()
            
            DBConnectionHandler.closeConnection(self, connection)

            dispatcher.utter_message(text= 'Ecco il link al corso ' + tracker.get_slot('course') + " " + "".join(course_link))
            
            return []

class ActionSetReminder(Action):    #TODO aggiungere email reminder? quando un nuovo corso è assegnato allo studente il bot gli manda una mail

    def name(self) -> Text:
        return "action_set_reminder"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        dispatcher.utter_message("Te lo ricordo tra 5 secondi")

        date = datetime.now() + timedelta(seconds=5)

        reminder = ReminderScheduled(
            "EXTERNAL_reminder",
            trigger_date_time=date,
            name="my_reminder",
            kill_on_user_message=False,
        )

        return [reminder]

class ActionReactToReminder(Action):

    def name(self) -> Text:
        return "action_react_to_reminder"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        dispatcher.utter_message("Ricordati di finire la lezione")

        return []
