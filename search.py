import json 
import os
current_file_path = __file__
current_file_dir = os.path.dirname(__file__)
class_json_path = os.path.join(current_file_dir, "json", "classes.json")
ratings_json_path = os.path.join(current_file_dir, "json", "Professor_Ratings.json")

class CourseInfo:
    def __init__(self, time, course_name_section, professor, days_of_week, section_number, prof_rating, class_code, section_num, course_name):
        self.time = time
        self.course_name_section = course_name_section
        self.professor = professor
        self.days_of_week = days_of_week
        self.section_number = section_number
        self.prof_rating = prof_rating
        self.class_code = class_code
        self.section_num = section_num
        self.course_name = course_name

def make_class_list(classesJson):
    class_file = open(classesJson)
    data = json.load(class_file)
    class_list = []

    for key in data:
        sections = []
        for section in data[key]["Sections"]:
            sections.append(section["Section Number"])
        class_list.append((key, sections))
    return class_list


def search_class(prefix, class_list, classesJson, ratingsJson):
    class_file = open(classesJson)
    ratings_file = open(ratingsJson)
    data = json.load(class_file)
    ratings_data = json.load(ratings_file)

    results = []
    for curr in class_list:
        class_code = curr[0]
        #if search matches, get additional information
        if class_code.upper().startswith(prefix.upper()):
            course_name = data[class_code]["Class Title"]
            professor = data[class_code]["Professors"]

            #get ratings if exist
            if ratings_data.get(professor):
                prof_rating = ratings_data[professor]["Level of Difficulty"]
            else:
                prof_rating = "N/A"
            
            for section in data[class_code]["Sections"]:
                original_time = section["Times"]
                string_time = original_time.split(" ")
                # print(string_time)

                #if doesn't meet
                if original_time == "Does Not Meet" or original_time == "Meets Online":
                    days_of_week = original_time
                    curr_time = "N/A"
                else:
                    days_of_week = string_time[0]
                    curr_time = string_time[1]
                    #if friday class exists
                    if len(string_time) > 3:
                        days_of_week = days_of_week + string_time[2]
                        curr_time = string_time[1] + " " + string_time[3]


                section_number = section["Section Number"]
                course_name_section = class_code + "-" + section_number + ": " + course_name 

                curr_course = CourseInfo(curr_time, course_name_section, professor, days_of_week, section_number, prof_rating, class_code, section_number, course_name)
                results.append(curr_course)
    return results

def filter_search(searched):
    class_list = make_class_list(class_json_path)
    results = search_class(searched, class_list, class_json_path, ratings_json_path)

    return results
