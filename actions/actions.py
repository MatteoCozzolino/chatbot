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

#Comandi UI rasa run --enable-api --cors “*” --debug 

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

        cursor.execute ("SELECT shortname FROM mdl_course WHERE mdl_course.id IN (SELECT mdl_enrol.courseid FROM mdl_user_enrolments INNER JOIN mdl_enrol ON mdl_user_enrolments.enrolid = mdl_enrol.id WHERE mdl_user_enrolments.userid = (SELECT mdl_user.id FROM mdl_user WHERE mdl_user.username = %s))", (username, ))
        courseName = cursor.fetchall()

        DBConnectionHandler.closeConnection(self, connection)

        return courseName

    def getCourseByName(self, courseName):
        connection = DBConnectionHandler.connect(self)
        cursor = connection.cursor()

        cursor.execute ("SELECT id FROM mdl_course WHERE shortname = %s", (courseName, ))
        courseid = cursor.fetchone()

        DBConnectionHandler.closeConnection(self, connection)

        return courseid

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

        cursor.execute("SELECT timestart from mdl_user_enrolments WHERE enrolid=25")    #TODO modificare
        time = cursor.fetchone()
        res = int(''.join(map(str, time)))/1000
        print(datetime.utcfromtimestamp(res).strftime('%d-%m-%Y %H:%M:%S'))

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
   
        dispatcher.utter_message(text = "Che corso vorresti seguire?", buttons = buttons)

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

class ActionGetLessonsList(Action):

    def name(self) -> Text:
        return "action_get_lessons_list"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
   
        connection = DBConnectionHandler.connect(self)
        cursor = connection.cursor()

        #Query che estrae le lezioni completate
        cursor.execute("SELECT instance FROM mdl_course_modules WHERE id IN (SELECT coursemoduleid FROM mdl_course_modules_completion WHERE userid = (SELECT mdl_user.id FROM mdl_user WHERE mdl_user.username = %s))", (username, ))
        lessonCompleted = cursor.fetchall()
        
        buttons=[]
        for i in lessonCompleted:
            cursor.execute("SELECT shortname FROM mdl_course WHERE id = (SELECT course FROM mdl_course_modules WHERE instance = %s)", (i))
            course_name = "".join(cursor.fetchone())
            cursor.execute("SELECT name FROM mdl_url WHERE id = %s", (i))
            lesson_name = "".join(cursor.fetchone())
            fill_slot = '{"lesson" : "' + str(i[0]) + '"}'
            buttons.append({"title": "Corso: " + course_name + " Lezione: " + lesson_name, "payload" : f'/lesson_selected{fill_slot}'})

        DBConnectionHandler.closeConnection(self, connection)
        
        dispatcher.utter_message(text = "Che lezione vorresti seguire?", buttons = buttons)

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

        cursor.execute ("SELECT fullname, summary, startdate, enddate FROM mdl_course WHERE mdl_course.shortname =  %s", (courseName, ))
        course_info = cursor.fetchone()

        fullName = course_info[0]
        summary = course_info[1]    #TODO da trovare il summary del corso
        startDate = course_info[2]
        endDate= course_info[3]
            
        DBConnectionHandler.closeConnection(self, connection)
        
        dispatcher.utter_message(text= 'Ecco le informazioni del corso ' + tracker.get_slot('course') + "\nNome completo: " + fullName + "\nRiassunto: " + 
        summary + "\nData d'inizio: " + datetime.utcfromtimestamp(startDate/1000).strftime('%d-%m-%Y %H:%M:%S')+ "\nData di fine: " + 
        datetime.utcfromtimestamp(endDate/1000).strftime('%d-%m-%Y %H:%M:%S'))

        return []

class ActionGetLink(Action):

     def name(self) -> Text:
        return "action_get_link"

     def run(self, dispatcher: CollectingDispatcher,
             tracker: Tracker,
             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

            connection = DBConnectionHandler.connect(self)
            cursor = connection.cursor(buffered = True)

            #La struttura gestisce l'action get_link in base a quale intent viene usato, recupera informazioni sapendo il corso ma non la lezione e viceversa
            if tracker.get_intent_of_latest_message() == "course_selected":
                courseName = tracker.get_slot('course')
                courseid = Courses.getCourseByName(self, courseName)
                cursor.execute("SELECT instance FROM mdl_course_modules WHERE course = " + str(courseid[0]) + " AND id IN (SELECT coursemoduleid FROM mdl_course_modules_completion WHERE userid = (SELECT mdl_user.id FROM mdl_user WHERE mdl_user.username = %s))", (username, ))
                lessons = cursor.fetchall()
                lastLesson = "".join(map(str, lessons[-1]))
                lessonid = int(lastLesson) + 1  
            elif tracker.get_intent_of_latest_message() == "lesson_selected":
                lessonid = tracker.get_slot('lesson')
                cursor.execute("SELECT shortname FROM mdl_course WHERE id = (SELECT course FROM mdl_course_modules WHERE instance = " + lessonid + ")")
                courseName= "".join(cursor.fetchone())

            cursor.execute ("SELECT externalurl FROM mdl_url WHERE id = %s", (lessonid,))
            course_link = cursor.fetchone()

            cursor.execute ("SELECT name FROM mdl_url WHERE id = %s", (lessonid,))
            lessonName = "".join(cursor.fetchone())

            DBConnectionHandler.closeConnection(self, connection)

            dispatcher.utter_message(text = "Ecco il link alla lezione " + str(lessonName) + " del corso " + str(courseName) + " " + "".join(course_link))
            
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
