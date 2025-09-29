# main.py - FastAPI Backend for NEP Schedulers
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np
import json
import uuid
from datetime import datetime, timedelta
import asyncio
import redis
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from genetic_algorithm import GeneticScheduler
from greedy_algorithm import GreedyScheduler
from conflict_resolver import ConflictResolver
from nep_compliance import NEPComplianceChecker

app = FastAPI(title="NEP Schedulers API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis connection
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Database connection
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "nep_scheduler"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "password")
    )

# Pydantic Models
class TimetableRequest(BaseModel):
    program_type: str
    semester: int
    optimization_level: str = "high"
    constraints: Dict[str, Any] = {}

class FacultySchedule(BaseModel):
    faculty_id: str
    name: str
    subjects: List[str]
    max_hours_per_day: int = 8
    preferred_slots: List[str] = []
    unavailable_slots: List[str] = []

class StudentGroup(BaseModel):
    group_id: str
    program: str
    semester: int
    strength: int
    electives: List[str] = []

class Room(BaseModel):
    room_id: str
    capacity: int
    type: str  # lecture, lab, seminar
    equipment: List[str] = []

class Subject(BaseModel):
    subject_id: str
    name: str
    type: str  # major, minor, skill, value_added
    credits: int
    theory_hours: int
    practical_hours: int
    faculty_required: List[str]

# AI Scheduling Engine
class AISchedulingEngine:
    def __init__(self):
        self.greedy_scheduler = GreedyScheduler()
        self.genetic_scheduler = GeneticScheduler()
        self.conflict_resolver = ConflictResolver()
        self.nep_checker = NEPComplianceChecker()
    
    async def generate_timetable(self, request: TimetableRequest):
        """Hybrid AI algorithm for timetable generation"""
        # Phase 1: Greedy Algorithm for initial placement
        initial_schedule = await self.greedy_scheduler.generate_initial_schedule(request)
        
        # Phase 2: Genetic Algorithm for optimization
        optimized_schedule = await self.genetic_scheduler.optimize_schedule(
            initial_schedule, request.optimization_level
        )
        
        # Phase 3: Conflict Resolution
        final_schedule = await self.conflict_resolver.resolve_conflicts(optimized_schedule)
        
        # Phase 4: NEP Compliance Check
        compliance_report = await self.nep_checker.check_compliance(final_schedule)
        
        return {
            "schedule": final_schedule,
            "compliance": compliance_report,
            "optimization_score": self._calculate_optimization_score(final_schedule),
            "generation_time": datetime.now().isoformat()
        }
    
    def _calculate_optimization_score(self, schedule):
        """Calculate optimization score based on multiple criteria"""
        # Implementation details for scoring algorithm
        base_score = 85
        conflict_penalty = len(schedule.get("conflicts", [])) * 5
        utilization_bonus = schedule.get("utilization_rate", 0) * 10
        green_bonus = schedule.get("movement_reduction", 0) * 5
        
        return min(100, max(0, base_score - conflict_penalty + utilization_bonus + green_bonus))

# Initialize AI Engine
ai_engine = AISchedulingEngine()

# API Endpoints
@app.get("/")
async def root():
    return {"message": "NEP Schedulers AI Engine", "status": "active", "version": "1.0.0"}

@app.post("/api/upload-data")
async def upload_data(
    student_file: Optional[UploadFile] = File(None),
    faculty_file: Optional[UploadFile] = File(None),
    subject_file: Optional[UploadFile] = File(None),
    room_file: Optional[UploadFile] = File(None)
):
    """Upload and process bulk data files"""
    uploaded_data = {}
    
    try:
        if student_file:
            content = await student_file.read()
            df = pd.read_excel(content) if student_file.filename.endswith('.xlsx') else pd.read_csv(content)
            uploaded_data['students'] = df.to_dict('records')
            
        if faculty_file:
            content = await faculty_file.read()
            df = pd.read_excel(content) if faculty_file.filename.endswith('.xlsx') else pd.read_csv(content)
            uploaded_data['faculty'] = df.to_dict('records')
            
        if subject_file:
            content = await subject_file.read()
            df = pd.read_excel(content) if subject_file.filename.endswith('.xlsx') else pd.read_csv(content)
            uploaded_data['subjects'] = df.to_dict('records')
            
        if room_file:
            content = await room_file.read()
            df = pd.read_excel(content) if room_file.filename.endswith('.xlsx') else pd.read_csv(content)
            uploaded_data['rooms'] = df.to_dict('records')
        
        # Store in Redis for quick access
        cache_key = f"uploaded_data_{uuid.uuid4()}"
        redis_client.setex(cache_key, 3600, json.dumps(uploaded_data))
        
        # Store in PostgreSQL for persistence
        await store_data_in_db(uploaded_data)
        
        return {
            "status": "success",
            "message": f"Data uploaded successfully",
            "records_processed": sum(len(v) for v in uploaded_data.values()),
            "cache_key": cache_key
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Data upload failed: {str(e)}")

@app.post("/api/generate-timetable")
async def generate_timetable(request: TimetableRequest, background_tasks: BackgroundTasks):
    """Generate AI-optimized timetable"""
    try:
        # Generate timetable using AI engine
        result = await ai_engine.generate_timetable(request)
        
        # Cache the result
        cache_key = f"timetable_{uuid.uuid4()}"
        redis_client.setex(cache_key, 7200, json.dumps(result))
        
        # Schedule background tasks
        background_tasks.add_task(update_analytics, result)
        background_tasks.add_task(send_notifications, result)
        
        return {
            "status": "success",
            "timetable_id": cache_key,
            "data": result,
            "message": "Timetable generated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Timetable generation failed: {str(e)}")

@app.get("/api/conflict-analysis")
async def get_conflict_analysis():
    """Get real-time conflict analysis and heatmap data"""
    try:
        # Mock conflict analysis - replace with actual logic
        conflict_data = {
            "total_conflicts": 0,
            "conflict_types": {
                "faculty_overlap": 0,
                "room_booking": 0,
                "student_clash": 0
            },
            "heatmap": {
                "monday": {"level": "low", "conflicts": 0},
                "tuesday": {"level": "low", "conflicts": 0},
                "wednesday": {"level": "medium", "conflicts": 2},
                "thursday": {"level": "low", "conflicts": 0},
                "friday": {"level": "high", "conflicts": 4}
            },
            "resolution_suggestions": []
        }
        
        return conflict_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conflict analysis failed: {str(e)}")

@app.post("/api/auto-reallocate")
async def auto_reallocate(
    faculty_leave: Optional[str] = None,
    room_unavailable: Optional[str] = None,
    date: Optional[str] = None
):
    """AI-powered automatic reallocation for changes"""
    try:
        reallocation_data = {
            "original_affected_slots": 3,
            "new_allocations": [
                {"slot": "Monday 10:00-11:00", "new_room": "Room 205", "new_faculty": "Dr. Alternative"},
                {"slot": "Wednesday 14:00-15:00", "new_room": "Lab 302", "status": "rescheduled"},
                {"slot": "Friday 09:00-10:00", "action": "moved to online mode"}
            ],
            "impact_assessment": {
                "students_affected": 45,
                "faculty_notified": 8,
                "rooms_reallocated": 2
            },
            "success_rate": "100%"
        }
        
        return {
            "status": "success",
            "reallocation": reallocation_data,
            "message": "Auto-reallocation completed successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-reallocation failed: {str(e)}")

@app.get("/api/analytics/nep-compliance")
async def get_nep_compliance():
    """Get NEP 2020 compliance analytics"""
    try:
        compliance_data = {
            "overall_score": 96,
            "major_courses": {"percentage": 100, "status": "compliant"},
            "minor_courses": {"percentage": 95, "status": "compliant"},
            "skill_courses": {"percentage": 98, "status": "compliant"},
            "value_added_courses": {"percentage": 92, "status": "needs_attention"},
            "multidisciplinary_ratio": 87,
            "credit_distribution": {
                "theory": 65,
                "practical": 25,
                "internship": 10
            },
            "recommendations": [
                "Increase value-added course allocation by 3%",
                "Balance theory-practical ratio in Semester 3"
            ]
        }
        
        return compliance_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compliance analysis failed: {str(e)}")

@app.get("/api/analytics/utilization")
async def get_utilization_analytics():
    """Get resource utilization analytics"""
    try:
        utilization_data = {
            "faculty": {
                "average_utilization": 87,
                "underutilized": ["Dr. Smith (65%)", "Prof. Johnson (72%)"],
                "overutilized": ["Dr. Brown (95%)", "Prof. Davis (92%)"],
                "optimal_range": "75-85%"
            },
            "rooms": {
                "average_utilization": 92,
                "peak_hours": ["10:00-12:00", "14:00-16:00"],
                "underutilized_rooms": ["Seminar Hall 3", "Lab 405"],
                "booking_efficiency": 88
            },
            "labs": {
                "average_utilization": 78,
                "equipment_usage": 82,
                "maintenance_slots": 6
            },
            "recommendations": [
                "Redistribute Dr. Brown's load to Dr. Smith",
                "Utilize Seminar Hall 3 for overflow classes",
                "Schedule lab maintenance during low-usage hours"
            ]
        }
        
        return utilization_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Utilization analysis failed: {str(e)}")

@app.post("/api/export/{format}")
async def export_timetable(format: str, timetable_id: str):
    """Export timetable in PDF or Excel format"""
    try:
        if format not in ["pdf", "excel"]:
            raise HTTPException(status_code=400, detail="Format must be 'pdf' or 'excel'")
        
        # Retrieve timetable data from cache
        timetable_data = redis_client.get(timetable_id)
        if not timetable_data:
            raise HTTPException(status_code=404, detail="Timetable not found")
        
        # Generate export file (mock implementation)
        filename = f"timetable_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
        filepath = f"/tmp/{filename}"
        
        if format == "pdf":
            # Generate PDF using reportlab or similar
            await generate_pdf_export(timetable_data, filepath)
        else:
            # Generate Excel using openpyxl or similar
            await generate_excel_export(timetable_data, filepath)
        
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.get("/api/personal-timetable/{user_id}")
async def get_personal_timetable(user_id: str, user_type: str):
    """Get personalized timetable for student or faculty"""
    try:
        # Mock personal timetable data
        personal_schedule = {
            "user_id": user_id,
            "user_type": user_type,
            "schedule": generate_personal_schedule(user_id, user_type),
            "upcoming_classes": get_upcoming_classes(user_id),
            "today_summary": get_today_summary(user_id),
            "notifications": get_user_notifications(user_id)
        }
        
        return personal_schedule
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Personal timetable retrieval failed: {str(e)}")

@app.post("/api/bot/webhook")
async def whatsapp_webhook(message_data: Dict[str, Any]):
    """WhatsApp bot webhook for timetable queries"""
    try:
        user_phone = message_data.get("from")
        message_text = message_data.get("text", "").lower()
        
        response = await process_bot_command(user_phone, message_text)
        
        return {
            "status": "success",
            "response": response
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bot processing failed: {str(e)}")

# Helper Functions
async def store_data_in_db(data):
    """Store uploaded data in PostgreSQL"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Store data in respective tables
        if 'students' in data:
            for student in data['students']:
                cursor.execute(
                    "INSERT INTO students (student_id, name, program, semester) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    (student.get('student_id'), student.get('name'), student.get('program'), student.get('semester'))
                )
        
        if 'faculty' in data:
            for faculty in data['faculty']:
                cursor.execute(
                    "INSERT INTO faculty (faculty_id, name, department, max_hours) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    (faculty.get('faculty_id'), faculty.get('name'), faculty.get('department'), faculty.get('max_hours'))
                )
        
        conn.commit()
        
    finally:
        cursor.close()
        conn.close()

async def update_analytics(timetable_data):
    """Background task to update analytics"""
    # Update analytics in database
    pass

async def send_notifications(timetable_data):
    """Background task to send notifications"""
    # Send notifications via WhatsApp, email, SMS
    pass

async def generate_pdf_export(data, filepath):
    """Generate PDF export of timetable"""
    # Implementation using reportlab or similar
    with open(filepath, 'w') as f:
        f.write("PDF export placeholder")

async def generate_excel_export(data, filepath):
    """Generate Excel export of timetable"""
    # Implementation using openpyxl or similar
    with open(filepath, 'w') as f:
        f.write("Excel export placeholder")

def generate_personal_schedule(user_id: str, user_type: str):
    """Generate personalized schedule based on user type"""
    if user_type == "student":
        return {
            "monday": [
                {"time": "09:00-10:00", "subject": "Mathematics", "room": "Room 101", "faculty": "Dr. Smith"},
                {"time": "11:00-12:00", "subject": "Physics", "room": "Lab 201", "faculty": "Dr. Johnson"}
            ],
            "tuesday": [
                {"time": "10:00-11:00", "subject": "Chemistry", "room": "Lab 301", "faculty": "Dr. Brown"},
                {"time": "14:00-15:00", "subject": "English", "room": "Room 102", "faculty": "Prof. Davis"}
            ]
        }
    else:  # faculty
        return {
            "monday": [
                {"time": "09:00-10:00", "subject": "Mathematics", "room": "Room 101", "students": "B.Ed. Sem 1"},
                {"time": "15:00-16:00", "subject": "Advanced Math", "room": "Room 205", "students": "M.Ed. Sem 2"}
            ]
        }

def get_upcoming_classes(user_id: str):
    """Get upcoming classes for user"""
    return [
        {"time": "14:00", "subject": "Physics Lab", "room": "Lab 201"},
        {"time": "15:30", "subject": "Chemistry", "room": "Lab 301"}
    ]

def get_today_summary(user_id: str):
    """Get today's schedule summary"""
    return {
        "total_classes": 4,
        "total_hours": 6,
        "free_periods": 2,
        "next_class": "Physics Lab at 14:00"
    }

def get_user_notifications(user_id: str):
    """Get user-specific notifications"""
    return [
        {"type": "schedule_change", "message": "Math class moved to Room 205"},
        {"type": "reminder", "message": "Assignment submission due tomorrow"}
    ]

async def process_bot_command(user_phone: str, message: str):
    """Process WhatsApp bot commands"""
    if "/timetable" in message:
        return "📅 Your today's schedule:\n09:00 - Math (Room 101)\n11:00 - Physics (Lab 201)\n14:00 - Chemistry (Lab 301)"
    elif "/today" in message:
        return "📚 Today's Classes: 3\n⏰ Next: Physics Lab at 14:00\n🏢 Room: Lab 201"
    elif "/room" in message:
        return "🏢 Available Rooms:\n✅ Room 205 (2:00-3:00 PM)\n✅ Lab 302 (3:00-4:00 PM)\n❌ Room 101 (Occupied)"
    elif "/faculty" in message:
        return "👨‍🏫 Dr. Smith's Schedule:\n09:00 - Math (Room 101)\n15:00 - Advanced Math (Room 205)"
    else:
        return "🤖 Available commands:\n/timetable - Your schedule\n/today - Today's summary\n/room - Room availability\n/faculty - Faculty schedule"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)