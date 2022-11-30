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
username = "user"   #TODO variabili temporanee con i dati dell'utente da dover estrarre dalla sessione in corso
userEmail = "user@mail.com"

#TEMP: ID dal DB per fare INSERT e testare le query
#userid = 3 
#courseid= 10,11,12 
#enrolid= 25,28,31

#TODO action per le lezioni

#La classe gestisce la connessione al DB
class DBConnectionHandler():

    def connect(self):

        connection = mysql.connect(host = DBADDRESS, user = DBUSERNAME, password = DBPW, database = DBNAME)
        
        return connection

    def closeConnection(self, connection):

        connection.commit()
        connection.close()

        return

class Courses():

    def getList(self):
        connection = DBConnectionHandler.connect(self)
        cursor = connection.cursor()

        #Query per estrarre i corsi a cui lo studente è iscritto
        cursor.execute ("SELECT shortname FROM mdl_course WHERE mdl_course.id IN (SELECT mdl_enrol.courseid FROM mdl_user_enrolments INNER JOIN mdl_enrol ON mdl_user_enrolments.enrolid = mdl_enrol.id WHERE mdl_user_enrolments.userid = (SELECT mdl_user.id FROM mdl_user WHERE mdl_user.username = %s))", (username, ))
        courseName = cursor.fetchall()

        DBConnectionHandler.closeConnection(self, connection)

        return courseName

class ActionGetCoursesList(Action):

    def name(self) -> Text:
        return "action_get_courses_list"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        courseName = Courses.getList(self)
    
        connection = DBConnectionHandler.connect(self)
        cursor = connection.cursor()

        #Query per estrarre i corsi che lo studente ha già completato
        cursor.execute("SELECT shortname FROM mdl_course WHERE mdl_course.id IN (SELECT mdl_course_completions.course FROM mdl_course_completions WHERE mdl_course_completions.userid = (SELECT mdl_user.id FROM mdl_user WHERE mdl_user.username = %s))", (username, ))
        coursesCompleted = cursor.fetchall()

        DBConnectionHandler.closeConnection(self, connection)
        buttons=[]

        #I corsi già completati sono eliminati dalla lista dei corsi che lo studente può seguire
        if len(coursesCompleted) > 0:
            for j in coursesCompleted:
                if courseName.count(j) > 0:
                    courseName.remove(j)
        for i in courseName:                
            tuple_to_str = "".join(i)        
            fill_slot = '{"course" : "' + tuple_to_str + '"}'
            buttons.append({"title": tuple_to_str, "payload" : f'/course_selected{fill_slot}'}) #TODO query per estrarre il tempo rimasto per finire un corso
   
        dispatcher.utter_message(text = "Che corsi vorresti seguire?", buttons = buttons)

        return []

class ActionGetCoursesEnrolled(Action):

     def name(self) -> Text:
        return "action_get_courses_enrolled"

     def run(self, dispatcher: CollectingDispatcher,
             tracker: Tracker,
             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        courseName = Courses.getList(self)
    
        buttons=[]
        for i in courseName:                
            tuple_to_str = "".join(i)        
            fill_slot = '{"course" : "' + tuple_to_str + '"}'
            buttons.append({"title": tuple_to_str, "payload" : f'/course_selected{fill_slot}'})
   
        dispatcher.utter_message(text = "Di quale corso vuoi più informazioni?", buttons = buttons)

        return []

class ActionGetCourseInfo(Action):

     def name(self) -> Text:
        return "action_get_course_info"

     def run(self, dispatcher: CollectingDispatcher,
             tracker: Tracker,
             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        connection = DBConnectionHandler.connect(self)
        cursor = connection.cursor(buffered = True)

        courseName = tracker.get_slot('course')

        cursor.execute ("SELECT fullname, shortname, summary, startdate, enddate FROM mdl_course WHERE mdl_course.shortname =  %s", (courseName, ))
        course_info = cursor.fetchall()
            
        DBConnectionHandler.closeConnection(self, connection)
        
        dispatcher.utter_message(text= 'Ecco le informazioni del corso ' + tracker.get_slot('course') + " " + " ".join(map(str, course_info)))    #TODO da elaborare per essere comprensibile

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

            dispatcher.utter_message(text= 'Ecco il link al corso ' + tracker.get_slot('course') + " " + "".join(course_link))  #TODO sostituire il link con "clicca qui" o simili
            
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
