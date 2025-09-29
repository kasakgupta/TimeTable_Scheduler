# greedy_algorithm.py - Greedy Algorithm for Initial Timetable Generation
from typing import Dict, List, Set, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from collections import defaultdict
import heapq

class Priority(Enum):
    """Priority levels for scheduling decisions"""
    HIGH = 1
    MEDIUM = 2
    LOW = 3

@dataclass
class TimeSlot:
    """Represents a time slot in the timetable"""
    day: int  # 0-4 (Monday-Friday)
    period: int  # 0-7 (periods in a day)
    
    def __hash__(self):
        return hash((self.day, self.period))
    
    def __eq__(self, other):
        return self.day == other.day and self.period == other.period

@dataclass
class SchedulingConstraint:
    """Represents various scheduling constraints"""
    faculty_id: str
    unavailable_slots: Set[TimeSlot] = field(default_factory=set)
    max_consecutive_hours: int = 3
    preferred_days: List[int] = field(default_factory=list)
    min_gap_between_classes: int = 0

@dataclass
class ClassRequirement:
    """Represents a class that needs to be scheduled"""
    subject_id: str
    subject_name: str
    faculty_id: str
    student_group_id: str
    room_type: str  # lecture, lab, seminar
    duration: int = 1  # number of periods
    weekly_frequency: int = 1
    priority: Priority = Priority.MEDIUM
    preferred_slots: List[TimeSlot] = field(default_factory=list)
    
    def __lt__(self, other):
        return self.priority.value < other.priority.value

class GreedyScheduler:
    """Greedy algorithm for initial timetable generation"""
    
    def __init__(self):
        self.schedule_matrix = {}  # [day][period] -> class_info
        self.faculty_schedule = defaultdict(set)  # faculty_id -> set of TimeSlots
        self.room_schedule = defaultdict(set)  # room_id -> set of TimeSlots
        self.group_schedule = defaultdict(set)  # group_id -> set of TimeSlots
        self.constraints = {}  # faculty_id -> SchedulingConstraint
        
        # Time slots configuration
        self.days = 5  # Monday to Friday
        self.periods_per_day = 8  # 9 AM to 5 PM
        self.time_slots = [
            "09:00-10:00", "10:00-11:00", "11:00-12:00", "12:00-13:00",
            "14:00-15:00", "15:00-16:00", "16:00-17:00", "17:00-18:00"
        ]
        
    async def generate_initial_schedule(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for greedy scheduling algorithm"""
        
        # Initialize scheduling environment
        self._initialize_schedule_matrix()
        
        # Parse input data
        class_requirements = await self._parse_class_requirements(request_data)
        available_rooms = await self._parse_room_data(request_data)
        faculty_constraints = await self._parse_faculty_constraints(request_data)
        
        # Store constraints
        self.constraints.update(faculty_constraints)
        
        # Priority-based scheduling
        scheduled_classes = await self._schedule_classes_greedily(
            class_requirements, available_rooms
        )
        
        # Generate final schedule format
        final_schedule = await self._generate_schedule_output(scheduled_classes)
        
        return final_schedule
    
    def _initialize_schedule_matrix(self):
        """Initialize empty schedule matrix"""
        self.schedule_matrix = {}
        for day in range(self.days):
            self.schedule_matrix[day] = {}
            for period in range(self.periods_per_day):
                self.schedule_matrix[day][period] = None
    
    async def _parse_class_requirements(self, request_data: Dict[str, Any]) -> List[ClassRequirement]:
        """Parse and prioritize class requirements"""
        requirements = []
        
        # Extract subjects and create class requirements
        subjects = request_data.get('subjects', [])
        student_groups = request_data.get('student_groups', [])
        
        for subject in subjects:
            for group in student_groups:
                # Check if this group needs this subject
                if self._group_needs_subject(group, subject):
                    # Determine priority based on subject type (NEP 2020 categories)
                    priority = self._determine_subject_priority(subject)
                    
                    # Calculate weekly frequency based on credits
                    weekly_freq = max(1, subject.get('credits',