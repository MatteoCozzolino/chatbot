from typing import Any, Text, Dict, List
from datetime import datetime, timedelta
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import ReminderScheduled, SlotSet
import mysql.connector as mysql

DBUSERNAME = "chatbot"
DBPW = "chatbotDB"
DBADDRESS = "35.232.172.36"
DBNAME = "h_farm"
username = "user"   #TODO variabili temporanee con i dati dell'utente da dover estrarre dalla sessione in corso
userEmail = "user@mail.com"

#Comandi UI rasa run -m models --enable-api --cors "*" --debug rasa run actions --cors "*" --debug

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

        DBConnectionHandler.closeConnection(self, connection)
        buttons=[]

        #I corsi già completati sono eliminati dalla lista dei corsi
        if len(coursesCompleted) > 0:
            for j in coursesCompleted:
                if courseName.count(j) > 0:
                    courseName.remove(j)
        for i in courseName:                
            tuple_to_str = "".join(i)        
            fill_slot = '{"course" : "' + tuple_to_str + '"}'
            buttons.append({"title": tuple_to_str, "payload" : f'/course_selected{fill_slot}'}) 

        if tracker.get_intent_of_latest_message() == "course_access":
            dispatcher.utter_message(text = "Che corso vorresti seguire? Fai click su uno dei pulsanti", buttons = buttons)
        elif tracker.get_intent_of_latest_message() == "course_info":
            dispatcher.utter_message(text = "Di quale corso vuoi più informazioni? Fai click su uno dei pulsanti", buttons = buttons)
        elif tracker.get_intent_of_latest_message() == "lessons_list":
            buttonsForLessons =[]
            for i in courseName:                
                tuple_to_str = "".join(i)        
                fill_slot = '{"course" : "' + tuple_to_str + '"}'
                buttonsForLessons.append({"title": tuple_to_str, "payload" : f'/course_selected{fill_slot}'}) 
            dispatcher.utter_message(text = "Di quale corso vuoi ripassare delle lezioni? Fai click su uno dei pulsanti", buttons = buttonsForLessons)

        return []

class ActionGetLessonsList(Action):

    def name(self) -> Text:
        return "action_get_lessons_list"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
   
        connection = DBConnectionHandler.connect(self)
        cursor = connection.cursor()

        courseName = tracker.get_slot('course')

        #Query che estrae le lezioni completate
        cursor.execute("SELECT instance FROM mdl_course_modules WHERE id IN (SELECT coursemoduleid FROM mdl_course_modules_completion WHERE userid = (SELECT mdl_user.id FROM mdl_user WHERE mdl_user.username = %s))", (username, ))
        lessonCompleted = cursor.fetchall()
        lessons=[]
        courseID = Courses.getCourseByName(self, courseName)
        cursor.execute("SELECT instance FROM mdl_course_modules WHERE course = %s", (courseID))
        lessonRequested = cursor.fetchall()
        if len(lessonCompleted) > 0:
            for j in lessonCompleted:
                if lessonRequested.count(j) == 1:
                    lessons.append(j)

        buttons=[]
        for i in lessons:
            cursor.execute("SELECT name FROM mdl_url WHERE id = %s", (i))
            lesson_name = "".join(cursor.fetchone())
            fill_slot = '{"lesson" : "' + ''.join(map(str, i)) + '"}'
            buttons.append({"title": "Lezione: " + lesson_name, "payload" : f'/lesson_selected{fill_slot}'})

        DBConnectionHandler.closeConnection(self, connection)
        
        dispatcher.utter_message(text = "Ecco le lezioni che puoi ripassare! Fai click su uno dei pulsanti", buttons = buttons)

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

        cursor.execute ("SELECT id, fullname, startdate, enddate FROM mdl_course WHERE mdl_course.shortname =  %s", (courseName, ))
        course_info = cursor.fetchone()

        courseID = course_info[0]
        fullName = course_info[1]
        startDate = course_info[2]
        endDate = course_info[3]

        cursor.execute("SELECT timestart from mdl_user_enrolments WHERE enrolid IN (SELECT id FROM mdl_enrol WHERE courseid = %s)", (courseID,))
        timeStart = cursor.fetchone()
        period = endDate - startDate
        res = int(''.join(map(str, timeStart)))
        timeLeft = period + res

        cursor.execute("SELECT count(*) FROM mdl_course_modules WHERE course = %s", (courseID,))
        totalLessons = cursor.fetchone()
        cursor.execute("SELECT count(*) FROM mdl_course_modules WHERE course = " + str(courseID) +" AND id IN (SELECT coursemoduleid FROM mdl_course_modules_completion WHERE userid = (SELECT mdl_user.id FROM mdl_user WHERE mdl_user.username = %s))", (username, ))
        finishedLessons = cursor.fetchone()
            
        DBConnectionHandler.closeConnection(self, connection)
        
        dispatcher.utter_message(text= 'Ecco le informazioni del corso ' + courseName + "\nNome completo: " + fullName + "\nIl tuo progresso: " + 
        ''.join(map(str, finishedLessons)) + " lezioni completate su " + ''.join(map(str, totalLessons)) + "\nData d'iscrizione: " + datetime.utcfromtimestamp(res).strftime('%d-%m-%Y %H:%M:%S')+ "\nData di fine: " + 
        datetime.utcfromtimestamp(timeLeft).strftime('%d-%m-%Y %H:%M:%S'))

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
                cursor.execute("SELECT mdl_user.id FROM mdl_user WHERE mdl_user.username = %s", (username, ))
                userid = cursor.fetchone()
                cursor.execute("SELECT instance FROM mdl_course_modules WHERE course = " + str(courseid[0]) + " AND id IN (SELECT coursemoduleid FROM mdl_course_modules_completion WHERE userid = %s)", (userid))
                lessons = cursor.fetchall()
                lastLesson = "".join(map(str, lessons[-1]))
                lessonid = int(lastLesson) + 1

                #Viene fatto un check per controllare se l'utente ha terminato il corso
                cursor.execute("SELECT course FROM mdl_course_modules WHERE instance = %s", (lessonid, ))
                instanceCourse = cursor.fetchone()
                if instanceCourse != courseid:
                    DBConnectionHandler.closeConnection(self, connection)
                    dispatcher.utter_message(text = "Non ci sono più lezioni disponibili per questo corso, ottimo lavoro!")
                    return [] 
            elif tracker.get_intent_of_latest_message() == "lesson_selected":
                lessonid = tracker.get_slot('lesson')
                cursor.execute("SELECT shortname FROM mdl_course WHERE id = (SELECT course FROM mdl_course_modules WHERE instance = " + lessonid + ")")
                courseName= "".join(cursor.fetchone())

            cursor.execute ("SELECT externalurl FROM mdl_url WHERE id = %s", (lessonid,))
            course_link = cursor.fetchone()

            cursor.execute ("SELECT name FROM mdl_url WHERE id = %s", (lessonid,))
            lessonName = "".join(cursor.fetchone())

            DBConnectionHandler.closeConnection(self, connection)

            if tracker.get_intent_of_latest_message() == "course_selected":
                dispatcher.utter_message(text = "Ecco il link alla lezione " + str(lessonName) + " " + "".join(course_link) + "\nDimmi quando hai finito e che voto hai preso 😀")
            elif tracker.get_intent_of_latest_message() == "lesson_selected":
                dispatcher.utter_message(text = "Ecco il link alla lezione " + str(lessonName) + " " + "".join(course_link))

            return [SlotSet("lesson", lessonid)]   

class ActionSetReminder(Action):    

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

class ActionGetLessonFeedback(Action):

    def name(self) -> Text:
        return "action_get_lesson_feedback"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker, 
        domain: Dict[Text, Any],) -> List[Dict[Text, Any]]:

        lesson_feedback_score = tracker.get_slot('feedback_score')
        if lesson_feedback_score == "brutto":
            normalized_feedback = 1
        elif lesson_feedback_score == "medio":
            normalized_feedback = 2
        elif lesson_feedback_score == "bello":
            normalized_feedback = 3
        lessonid = tracker.get_slot('lesson')
        mark = tracker.get_slot('mark') 

        connection = DBConnectionHandler.connect(self)
        cursor = connection.cursor(buffered = True)

        cursor.execute("SELECT mdl_user.id FROM mdl_user WHERE mdl_user.username = %s", (username, ))
        userid = cursor.fetchone()
        cursor.execute("SELECT id FROM mdl_course_modules WHERE instance = %s", (lessonid, ))
        moduleid = cursor.fetchone()
        cursor.execute("SELECT max(id) FROM mdl_course_modules_completion") 
        maxid = cursor.fetchone()
        cursor.execute("INSERT INTO mdl_course_modules_completion VALUES (%s,%s,%s,1,1,NULL,%s)", (int(''.join(map(str, maxid))) + 1 , int(''.join(map(str, moduleid))), int(''.join(map(str, userid))), datetime.timestamp(datetime.now())))

        #Tabella mdl_modules_feedback: id, moduleid, feedbackscore, mark, userid, timestamp
        
        cursor.execute("SELECT max(id) FROM mdl_modules_feedback") 
        id = cursor.fetchone()
    
        if ''.join(map(str, id)) == "None":
            currentid = 0
        else:
            currentid = int(''.join(map(str, id)))
        
        cursor.execute("INSERT INTO mdl_modules_feedback VALUES (%s,%s,%s,%s,%s,%s)", (currentid + 1 , int(''.join(map(str, moduleid))),  normalized_feedback,  mark, int(''.join(map(str, userid))), datetime.timestamp(datetime.now())))

        DBConnectionHandler.closeConnection(self, connection)

        return []

class ActionGetTimeLeft(Action):

    def name(self) -> Text:
        return "action_get_time_left"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker, 
        domain: Dict[Text, Any],) -> List[Dict[Text, Any]]:

        connection = DBConnectionHandler.connect(self)
        cursor = connection.cursor(buffered=True)

        cursor.execute("SELECT mdl_user.id FROM mdl_user WHERE mdl_user.username = %s", (username, ))
        userid = cursor.fetchone()

        cursor.execute("SELECT mdl_enrol.courseid FROM mdl_user_enrolments INNER JOIN mdl_enrol ON mdl_user_enrolments.enrolid = mdl_enrol.id WHERE mdl_user_enrolments.userid = (SELECT mdl_user.id FROM mdl_user WHERE mdl_user.username = %s)", (username, ))
        courseIDs = cursor.fetchall()

        cursor.execute("SELECT mdl_course_completions.course FROM mdl_course_completions WHERE mdl_course_completions.userid = (SELECT mdl_user.id FROM mdl_user WHERE mdl_user.username = %s)", (username, ))
        coursesCompleted = cursor.fetchall()

        if len(coursesCompleted) > 0:
            for j in coursesCompleted:
                if courseIDs.count(j) > 0:
                    courseIDs.remove(j)

        #Ad ogni courseID viene associato il timestamp relativo all'iscrizione al corso
        coursesTimeStartDict = dict()
        for j in courseIDs:
            cursor.execute("SELECT timestart FROM mdl_user_enrolments INNER JOIN mdl_enrol ON mdl_user_enrolments.enrolid = mdl_enrol.id WHERE userid = " + ''.join(map(str, userid)) + " AND courseid = %s", (str(j[0]),))
            timestart = cursor.fetchone()
            coursesTimeStartDict[j[0]] = int(''.join(map(str, timestart)))

        dictKeys = coursesTimeStartDict.keys()
        coursesTimeData = dict()
        for i in dictKeys:
            cursor.execute("SELECT startdate FROM mdl_course WHERE id = "+ str(i) +"")
            startdate = cursor.fetchone()
            cursor.execute("SELECT enddate FROM mdl_course WHERE id = "+ str(i) +"")
            enddate = cursor.fetchone()
            courseDuration = int(''.join(map(str, enddate))) - int(''.join(map(str, startdate)))
            endCourse = courseDuration + coursesTimeStartDict[i]   #La data della fine del corso
            currentTime = datetime.timestamp(datetime.now())
            timeLeft = endCourse - currentTime

            cursor.execute ("SELECT shortname FROM mdl_course WHERE id = "+ str(i) +"")
            courseName = "".join(cursor.fetchone())

            coursesTimeData[i] = [courseName, timeLeft]

        DBConnectionHandler.closeConnection(self, connection)

        message = "Ricordati che c'è un tempo limite per i corsi, ecco un aggiornamento per te:"
        for i in dictKeys:
            weeks = (coursesTimeData[i])[1]//604800
            days = ((coursesTimeData[i])[1] - weeks*604800)//86400
            hours = (((coursesTimeData[i])[1] - weeks*604800) - days*86400)//3600
            message = message + ("\nDel corso " + (coursesTimeData[i])[0] + " hai ancora " + str(int(weeks)) + " settimane, " + str(int(days)) + " giorni e " + str(int(hours)) + " ore. ")

        dispatcher.utter_message(text = message + "\nPer vedere la data di fine dei corsi ed altre informazioni fai click sul pulsante qui sotto sulla destra!")

        return []

