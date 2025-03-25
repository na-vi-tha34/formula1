from fastapi import FastAPI, Request, Form, status, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.auth.transport import requests
from google.cloud import firestore
from datetime import datetime
import google.oauth2.id_token
import re
from urllib.parse import urlencode

app = FastAPI()

firestore_db = firestore.Client()
firebase_request_adapter = requests.Request()
app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory="templates")

token = None 

# Index Route
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    id_token = request.cookies.get("token")
    error_message = request.query_params.get("error", None)
    success_message = request.query_params.get("success", None)
    user_token = None

    if id_token:
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            if user_token:
                return RedirectResponse(url="/dashboard")  # Redirect authenticated users
        except ValueError as err:
            print(str(err))

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "user_token": user_token, "error_message": error_message, "success_message": success_message},
    )

# Dashboard Route
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    id_token = request.cookies.get("token")

    if not id_token:
        return RedirectResponse(url="/?error=Please login first.")

    try:
        user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
        if not user_token:
            return RedirectResponse(url="/?error=Invalid session. Please log in again.")
    except ValueError as err:
        print(str(err))
        return RedirectResponse(url="/?error=Session error. Please log in again.")

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user_token": user_token},
    )


# Check if User is Authenticated
async def get_current_user(request: Request):
    id_token = request.cookies.get("token")

    if not id_token:
        raise HTTPException(
            status_code=303,
            detail="Unauthorized access. Redirecting to login.",
            headers={"Location": "/?error=Please log in first"}
        )

    try:
        user = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
        if not user:
            raise HTTPException(
                status_code=303,
                detail="Invalid session. Redirecting to login.",
                headers={"Location": "/?error=Invalid session, please log in again"}
            )
        return user  # User is authenticated
    except ValueError:
        raise HTTPException(
            status_code=303,
            detail="Authentication error. Redirecting to login.",
            headers={"Location": "/?error=Authentication error, please log in again"}
        )

# Route to Render Add Driver Page (Only for Logged-in Users)
@app.get("/add-driver", response_class=HTMLResponse)
async def add_driver_page(request: Request, user: dict = Depends(get_current_user)):
    success_message = request.query_params.get("success")
    return templates.TemplateResponse(
        "add_driver.html",
        {"request": request, "success_message": success_message}
    )

# Route to Add Driver to Firestore (Restricted to Logged-in Users)
@app.post("/add-driver")
async def add_driver(
    request: Request,
    name: str = Form(...),
    age: int = Form(...),
    total_pole_positions: int = Form(...),
    total_race_wins: int = Form(...),
    total_points_scored: float = Form(...),
    total_world_titles: int = Form(...),
    total_fastest_laps: int = Form(...),
    team: str = Form(...),
    user: dict = Depends(get_current_user),  # Ensure user is logged in
):
    drivers_collection = firestore_db.collection("drivers")

    # Check if driver already exists (Prevent duplicate names)
    existing_drivers = drivers_collection.where("name", "==", name).get()
    if existing_drivers:  # Firestore returns a list, even if empty
        return JSONResponse({"error": "Driver with this name already exists!"}, status_code=400)

    driver_data = {
        "name": name,
        "age": age,
        "total_pole_positions": total_pole_positions,
        "total_race_wins": total_race_wins,
        "total_points_scored": total_points_scored,
        "total_world_titles": total_world_titles,
        "total_fastest_laps": total_fastest_laps,
        "team": team
    }

    # Save to Firestore
    drivers_collection.add(driver_data)
    
    return RedirectResponse(url="/add-driver?success=Driver added successfully!", status_code=303)

# Route to Render Add Team Page (Only for Logged-in Users)
@app.get("/add-team", response_class=HTMLResponse)
async def add_team_page(request: Request, user: dict = Depends(get_current_user)):
    # If user is not authenticated, they will be redirected to "/"
    if isinstance(user, RedirectResponse):
        return user

    success_message = request.query_params.get("success")
    return templates.TemplateResponse("add_team.html", {"request": request, "success_message": success_message})

# Route to Add Team to Firestore (Restricted to Logged-in Users)
@app.post("/add-team")
async def add_team(
    request: Request,
    name: str = Form(...),
    year_founded: int = Form(...),
    total_pole_positions: int = Form(...),
    total_race_wins: int = Form(...),
    total_constructor_titles: int = Form(...),
    finishing_position_last_season: int = Form(...),
    user: dict = Depends(get_current_user),  # Ensure user is logged in
):
    # If user is not authenticated, they will be redirected to "/"
    if isinstance(user, RedirectResponse):
        return user

    teams_collection = firestore_db.collection("teams")

    # Check if team already exists (Prevent duplicate names)
    existing_team = teams_collection.where("name", "==", name).get()
    if existing_team:
        return JSONResponse({"error": "A team with this name already exists!"}, status_code=400)

    team_data = {
        "name": name,
        "year_founded": year_founded,
        "total_pole_positions": total_pole_positions,
        "total_race_wins": total_race_wins,
        "total_constructor_titles": total_constructor_titles,
        "finishing_position_last_season": finishing_position_last_season
    }

    # Save to Firestore
    teams_collection.add(team_data)
    return RedirectResponse(url="/add-team?success=Team added successfully!", status_code=303)

# Route to render the Query Drivers Page (Accessible to Everyone)
@app.get("/query-drivers", response_class=HTMLResponse)
async def query_drivers_page(request: Request):
    return templates.TemplateResponse("query_drivers.html", {"request": request, "drivers": None})

# Route to Process Driver Query
@app.post("/query-drivers", response_class=HTMLResponse)
async def query_drivers(
    request: Request,
    attribute: str = Form(...),
    operator: str = Form(...),
    value: float = Form(...)
):
    drivers_collection = firestore_db.collection("drivers")

    # Define Firestore query based on user selection
    if operator == "equal":
        query_ref = drivers_collection.where(attribute, "==", value)
    elif operator == "greater":
        query_ref = drivers_collection.where(attribute, ">", value)
    elif operator == "less":
        query_ref = drivers_collection.where(attribute, "<", value)
    else:
        query_ref = None

    drivers = []
    if query_ref:
        results = query_ref.stream()
        for doc in results:
            driver = doc.to_dict()
            driver["id"] = doc.id  # Store document ID for hyperlinking
            drivers.append(driver)

    return templates.TemplateResponse("query_drivers.html", {"request": request, "drivers": drivers})

# Route to View Individual Driver Details
@app.get("/driver/{driver_id}", response_class=HTMLResponse)
async def driver_details(request: Request, driver_id: str):
    driver_doc = firestore_db.collection("drivers").document(driver_id).get()
    if not driver_doc.exists:
        return templates.TemplateResponse("driver_not_found.html", {"request": request})

    driver_data = driver_doc.to_dict()
    return templates.TemplateResponse("driver_details.html", {"request": request, "driver": driver_data})

# Route to render the Query Teams Page (Accessible to Everyone)
@app.get("/query-teams", response_class=HTMLResponse)
async def query_teams_page(request: Request):
    return templates.TemplateResponse("query_teams.html", {"request": request, "teams": None})

# Route to Process Team Query
@app.post("/query-teams", response_class=HTMLResponse)
async def query_teams(
    request: Request,
    attribute: str = Form(...),
    operator: str = Form(...),
    value: float = Form(...)
):
    teams_collection = firestore_db.collection("teams")

    # Define Firestore query based on user selection
    if operator == "equal":
        query_ref = teams_collection.where(attribute, "==", value)
    elif operator == "greater":
        query_ref = teams_collection.where(attribute, ">", value)
    elif operator == "less":
        query_ref = teams_collection.where(attribute, "<", value)
    else:
        query_ref = None

    teams = []
    if query_ref:
        results = query_ref.stream()
        for doc in results:
            team = doc.to_dict()
            team["id"] = doc.id  # Store document ID for hyperlinking
            teams.append(team)

    return templates.TemplateResponse("query_teams.html", {"request": request, "teams": teams})

# Route to View Individual Team Details
@app.get("/team/{team_id}", response_class=HTMLResponse)
async def team_details(request: Request, team_id: str):
    team_doc = firestore_db.collection("teams").document(team_id).get()
    if not team_doc.exists:
        return templates.TemplateResponse("team_not_found.html", {"request": request})

    team_data = team_doc.to_dict()
    return templates.TemplateResponse("team_details.html", {"request": request, "team": team_data})

# Route to Display All Drivers (Only for Logged-in Users)
@app.get("/view-drivers", response_class=HTMLResponse)
async def view_drivers(request: Request, user: dict = Depends(get_current_user)):
    drivers_collection = firestore_db.collection("drivers")
    drivers = []

    results = drivers_collection.stream()
    for doc in results:
        driver = doc.to_dict()
        driver["id"] = doc.id  # Store document ID for hyperlinking
        drivers.append(driver)

    return templates.TemplateResponse("view_drivers.html", {"request": request, "drivers": drivers})


# Route to Render Edit Driver Page (Only for Logged-in Users)
@app.get("/edit-driver/{driver_id}", response_class=HTMLResponse)
async def edit_driver_page(request: Request, driver_id: str, user: dict = Depends(get_current_user)):
    driver_doc = firestore_db.collection("drivers").document(driver_id).get()

    if not driver_doc.exists:
        return RedirectResponse(url="/view-drivers?error=Driver not found", status_code=303)

    driver_data = driver_doc.to_dict()
    return templates.TemplateResponse("edit_driver.html", {"request": request, "driver": driver_data, "driver_id": driver_id})


# Route to Update Driver (Only for Logged-in Users)
@app.post("/update-driver/{driver_id}")
async def update_driver(
    request: Request,
    driver_id: str,
    name: str = Form(...),
    age: int = Form(...),
    total_pole_positions: int = Form(...),
    total_race_wins: int = Form(...),
    total_points_scored: float = Form(...),
    total_world_titles: int = Form(...),
    total_fastest_laps: int = Form(...),
    team: str = Form(...),
    user: dict = Depends(get_current_user)  # Ensure user is logged in
):
    drivers_collection = firestore_db.collection("drivers")
    driver_ref = drivers_collection.document(driver_id)

    # Check if driver exists
    driver_doc = driver_ref.get()
    if not driver_doc.exists:
        return RedirectResponse(url="/view-drivers?error=Driver not found", status_code=303)

    # Prevent duplicate driver names except for the current one
    existing_driver = drivers_collection.where("name", "==", name).get()
    if existing_driver and existing_driver[0].id != driver_id:
        return RedirectResponse(url=f"/edit-driver/{driver_id}?error=Another driver with this name already exists!", status_code=303)

    updated_data = {
        "name": name,
        "age": age,
        "total_pole_positions": total_pole_positions,
        "total_race_wins": total_race_wins,
        "total_points_scored": total_points_scored,
        "total_world_titles": total_world_titles,
        "total_fastest_laps": total_fastest_laps,
        "team": team,
    }

    driver_ref.update(updated_data)
    return RedirectResponse(url="/view-drivers?success=Driver updated successfully!", status_code=303)


# Route to Delete Driver (Only for Logged-in Users)
@app.get("/delete-driver/{driver_id}")
async def delete_driver(driver_id: str, user: dict = Depends(get_current_user)):
    driver_ref = firestore_db.collection("drivers").document(driver_id)
    driver_doc = driver_ref.get()

    if not driver_doc.exists:
        return RedirectResponse(url="/view-drivers?error=Driver not found", status_code=303)

    driver_ref.delete()
    return RedirectResponse(url="/view-drivers?success=Driver deleted successfully!", status_code=303)

# Route to Display All Teams (Only for Logged-in Users)
@app.get("/view-teams", response_class=HTMLResponse)
async def view_teams(request: Request, user: dict = Depends(get_current_user)):
    teams_collection = firestore_db.collection("teams")
    teams = []

    results = teams_collection.stream()
    for doc in results:
        team = doc.to_dict()
        team["id"] = doc.id  # Store document ID for hyperlinking
        teams.append(team)

    return templates.TemplateResponse("view_teams.html", {"request": request, "teams": teams})


# Route to Render Edit Team Page (Only for Logged-in Users)
@app.get("/edit-team/{team_id}", response_class=HTMLResponse)
async def edit_team_page(request: Request, team_id: str, user: dict = Depends(get_current_user)):
    team_doc = firestore_db.collection("teams").document(team_id).get()

    if not team_doc.exists:
        return RedirectResponse(url="/view-teams?error=Team not found", status_code=303)

    team_data = team_doc.to_dict()
    return templates.TemplateResponse("edit_team.html", {"request": request, "team": team_data, "team_id": team_id})


# Route to Update Team (Only for Logged-in Users)
@app.post("/update-team/{team_id}")
async def update_team(
    request: Request,
    team_id: str,
    name: str = Form(...),
    year_founded: int = Form(...),
    total_pole_positions: int = Form(...),
    total_race_wins: int = Form(...),
    total_constructor_titles: int = Form(...),
    finishing_position_last_season: int = Form(...),
    user: dict = Depends(get_current_user)  # Ensure user is logged in
):
    teams_collection = firestore_db.collection("teams")
    team_ref = teams_collection.document(team_id)

    # Check if team exists
    team_doc = team_ref.get()
    if not team_doc.exists:
        return RedirectResponse(url="/view-teams?error=Team not found", status_code=303)

    # Prevent duplicate team names except for the current one
    existing_team = teams_collection.where("name", "==", name).get()
    if existing_team and existing_team[0].id != team_id:
        return RedirectResponse(url=f"/edit-team/{team_id}?error=Another team with this name already exists!", status_code=303)

    updated_data = {
        "name": name,
        "year_founded": year_founded,
        "total_pole_positions": total_pole_positions,
        "total_race_wins": total_race_wins,
        "total_constructor_titles": total_constructor_titles,
        "finishing_position_last_season": finishing_position_last_season,
    }

    team_ref.update(updated_data)
    return RedirectResponse(url="/view-teams?success=Team updated successfully!", status_code=303)


# Route to Delete Team (Only for Logged-in Users)
@app.get("/delete-team/{team_id}")
async def delete_team(team_id: str, user: dict = Depends(get_current_user)):
    team_ref = firestore_db.collection("teams").document(team_id)
    team_doc = team_ref.get()

    if not team_doc.exists:
        return RedirectResponse(url="/view-teams?error=Team not found", status_code=303)

    team_ref.delete()
    return RedirectResponse(url="/view-teams?success=Team deleted successfully!", status_code=303)

# Route to Render Driver Comparison Page (Only for Logged-in Users)
@app.get("/compare-drivers", response_class=HTMLResponse)
async def compare_drivers_page(request: Request, user: dict = Depends(get_current_user)):
    drivers_collection = firestore_db.collection("drivers")
    drivers = []

    # Fetch all drivers from Firestore
    results = drivers_collection.stream()
    for doc in results:
        driver = doc.to_dict()
        driver["id"] = doc.id  # Store document ID
        drivers.append(driver)

    return templates.TemplateResponse(
        "compare_drivers.html",
        {"request": request, "drivers": drivers, "driver1": None, "driver2": None}
    )

# Route to Process Driver Comparison (Only for Logged-in Users)
@app.post("/compare-drivers", response_class=HTMLResponse)
async def compare_drivers(
    request: Request,
    driver1: str = Form(...),
    driver2: str = Form(...),
    user: dict = Depends(get_current_user)  # Ensures only logged-in users can compare
):
    drivers_collection = firestore_db.collection("drivers")

    # Fetch the selected drivers
    driver1_doc = drivers_collection.document(driver1).get()
    driver2_doc = drivers_collection.document(driver2).get()

    if not driver1_doc.exists or not driver2_doc.exists:
        return RedirectResponse(url="/compare-drivers?error=One or both drivers not found", status_code=303)

    driver1_data = driver1_doc.to_dict()
    driver2_data = driver2_doc.to_dict()

    return templates.TemplateResponse(
        "compare_drivers.html",
        {
            "request": request,
            "drivers": drivers_collection.stream(),
            "driver1": driver1_data,
            "driver2": driver2_data
        }
    )

# Route to Render Team Comparison Page (Form to Select Teams)
@app.get("/compare-teams", response_class=HTMLResponse)
async def compare_teams_page(request: Request, user: dict = Depends(get_current_user)):
    teams_collection = firestore_db.collection("teams")
    teams = []

    # Fetch all teams from Firestore
    results = teams_collection.stream()
    for doc in results:
        team = doc.to_dict()
        team["id"] = doc.id  # Store document ID
        teams.append(team)

    return templates.TemplateResponse("compare_teams.html", {"request": request, "teams": teams, "team1": None, "team2": None})

# Route to Process Team Comparison
@app.post("/compare-teams", response_class=HTMLResponse)
async def compare_teams(
    request: Request,
    team1: str = Form(...),
    team2: str = Form(...),
    user: dict = Depends(get_current_user)  # Ensure only logged-in users can compare
):
    teams_collection = firestore_db.collection("teams")

    # Fetch the selected teams
    team1_doc = teams_collection.document(team1).get()
    team2_doc = teams_collection.document(team2).get()

    if not team1_doc.exists or not team2_doc.exists:
        return RedirectResponse(url="/compare-teams?error=One or both teams not found", status_code=303)

    team1_data = team1_doc.to_dict()
    team2_data = team2_doc.to_dict()

    return templates.TemplateResponse(
        "compare_teams.html",
        {"request": request, "teams": teams_collection.stream(), "team1": team1_data, "team2": team2_data}
    )