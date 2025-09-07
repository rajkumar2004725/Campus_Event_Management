Prototype for Campus Event Management  


This repository includes a simple campus event management system prototype. It was created to demonstrate a platform for scalable event registration and reporting. The system uses a SQLite database and FastAPI. It provides RESTful APIs for managing events, handling registrations, tracking attendance, collecting feedback, and generating reports. Following the project's requirements, there is a web-based Admin Portal and a mobile-simulated Student App. A basic HTML/JS frontend is available for both admin and student interfaces.  

The goal is to create a prototype for organizing college events, such as workshops, fests, and seminars. This system provides tools for staff to plan and oversee activities. It also enables students to sign up, participate, and give feedback. Additionally, the prototype includes statistics on student participation and event popularity.  
Technology:  
Backend: SQLAlchemy, SQLite, and FastAPI  
Front-end: HTML  
Campus.db is a SQLite database.  


Setup Instructions

Clone the Repository:

    git clone https://github.com/rajkumar2004725/Campus_Event_Management.git
    cd Event_Management

Set Up Virtual Environment:

    python -m venv myenv
    myenv\Scripts\activate  # On Windows

Install Dependencies: Install required packages from requirements.txt:

    python -m pip install -r requirements.txt

Run the Server: Start the FastAPI server with:

    uvicorn main:app --reload --port 8001


To explore or to test its end points visit that page.

    http://127.0.0.1:8001/docs

Run the Frontend:

    Open admin_index.html and student_index.html in a web browser (e.g., double-click or use a Live Server extension in VS Code).
    Ensure the server is running, as the frontend calls http://localhost:8001 APIs.


API Endpoints

Admin Endpoints

These endpoints are intended for college staff to manage events,there is no authentication in prototype.


POST /events

Description: Create a new event.
              Used by an admin to create new events.

Request Body:

    {
      "name": "string",
      "type": "string",  // e.g., "Workshop", "Fest", "Seminar"
      "date": "2025-09-10T10:00:00",
      "college_id": 1
    }



GET /events
Description: List all events.
this is used by both admin and students to list all the events which are hosted.
if the college id is entered then we can specifically get the events hosted by that perticular college.

Query Parameters:
college_id (optional, integer): Filter by college ID.



Response: 200 OK with list of events.

    [
      {
        "id": 1,
        "name": "Hackathon",
        "type": "Workshop",
        "date": "2025-09-07T00:00:00",
        "college_id": 1,
        "cancelled": false
      }
    ]



PATCH /events/{event_id}

Description: Update an event (currently toggles cancellation status).

Path Parameter: event_id (integer)

Request Body:

    {
      "cancelled": true
    }
    


Response: 200 OK with updated event.

{
  "id": 1,
  "name": "Hackathon",
  "type": "Workshop",
  "date": "2025-09-07T00:00:00",
  "college_id": 1,
  "cancelled": true
}

Use Case: Admin cancels an event.
