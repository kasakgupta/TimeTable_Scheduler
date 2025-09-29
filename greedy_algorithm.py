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
                    weekly_freq = max(1, subject.get('credits', 3) // 2)
                    
                    # Create class requirement for theory
                    if subject.get('theory_hours', 0) > 0:
                        req = ClassRequirement(
                            subject_id=subject.get('subject_id', ''),
                            subject_name=subject.get('name', ''),
                            faculty_id=subject.get('faculty_id', ''),
                            student_group_id=group.get('group_id', ''),
                            room_type='lecture',
                            duration=1,
                            weekly_frequency=weekly_freq,
                            priority=priority
                        )
                        requirements.append(req)
                    
                    # Create class requirement for practical
                    if subject.get('practical_hours', 0) > 0:
                        req = ClassRequirement(
                            subject_id=subject.get('subject_id', '') + '_lab',
                            subject_name=subject.get('name', '') + ' Lab',
                            faculty_id=subject.get('faculty_id', ''),
                            student_group_id=group.get('group_id', ''),
                            room_type='lab',
                            duration=2,  # Labs typically take 2 hours
                            weekly_frequency=max(1, weekly_freq // 2),
                            priority=priority
                        )
                        requirements.append(req)
        
        # Sort by priority (HIGH -> MEDIUM -> LOW)
        requirements.sort()
        
        return requirements
    
    async def _parse_room_data(self, request_data: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """Parse available rooms by type"""
        rooms = request_data.get('rooms', [])
        
        rooms_by_type = {
            'lecture': [],
            'lab': [],
            'seminar': []
        }
        
        for room in rooms:
            room_type = room.get('type', 'lecture')
            if room_type in rooms_by_type:
                rooms_by_type[room_type].append(room)
        
        return rooms_by_type
    
    async def _parse_faculty_constraints(self, request_data: Dict[str, Any]) -> Dict[str, SchedulingConstraint]:
        """Parse faculty constraints and preferences"""
        constraints = {}
        
        faculty_list = request_data.get('faculty', [])
        
        for faculty in faculty_list:
            faculty_id = faculty.get('faculty_id', '')
            
            # Parse unavailable slots
            unavailable = set()
            for slot_str in faculty.get('unavailable_slots', []):
                # Parse slot string like "Monday_2" to TimeSlot
                if '_' in slot_str:
                    day_name, period = slot_str.split('_')
                    day_idx = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'].index(day_name.lower())
                    unavailable.add(TimeSlot(day_idx, int(period)))
            
            # Parse preferred days
            preferred_days = []
            for day_name in faculty.get('preferred_days', []):
                day_idx = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'].index(day_name.lower())
                preferred_days.append(day_idx)
            
            constraint = SchedulingConstraint(
                faculty_id=faculty_id,
                unavailable_slots=unavailable,
                max_consecutive_hours=faculty.get('max_consecutive_hours', 3),
                preferred_days=preferred_days,
                min_gap_between_classes=faculty.get('min_gap', 0)
            )
            
            constraints[faculty_id] = constraint
        
        return constraints
    
    def _group_needs_subject(self, group: Dict, subject: Dict) -> bool:
        """Check if a student group needs a particular subject"""
        # Check program compatibility
        group_program = group.get('program', '').lower()
        subject_programs = [p.lower() for p in subject.get('programs', [])]
        
        if subject_programs and group_program not in subject_programs:
            return False
        
        # Check semester compatibility
        group_semester = group.get('semester', 0)
        subject_semester = subject.get('semester', 0)
        
        return group_semester == subject_semester
    
    def _determine_subject_priority(self, subject: Dict) -> Priority:
        """Determine scheduling priority based on NEP 2020 subject type"""
        subject_type = subject.get('type', '').lower()
        
        # Major and core subjects get highest priority
        if subject_type in ['major', 'core']:
            return Priority.HIGH
        
        # Minor and skill-based get medium priority
        elif subject_type in ['minor', 'skill', 'ability_enhancement']:
            return Priority.MEDIUM
        
        # Value-added and electives get lower priority
        else:
            return Priority.LOW
    
    async def _schedule_classes_greedily(
        self, 
        requirements: List[ClassRequirement],
        available_rooms: Dict[str, List[Dict]]
    ) -> List[Dict[str, Any]]:
        """Greedily schedule classes based on priority and constraints"""
        
        scheduled_classes = []
        
        for req in requirements:
            # Schedule based on weekly frequency
            for occurrence in range(req.weekly_frequency):
                # Find best available slot
                best_slot = await self._find_best_slot(req, available_rooms)
                
                if best_slot:
                    slot, room = best_slot
                    
                    # Allocate the slot
                    class_info = {
                        'subject_id': req.subject_id,
                        'subject_name': req.subject_name,
                        'faculty_id': req.faculty_id,
                        'student_group_id': req.student_group_id,
                        'room_id': room['room_id'],
                        'room_name': room.get('name', room['room_id']),
                        'day': slot.day,
                        'period': slot.period,
                        'time_slot': self.time_slots[slot.period],
                        'duration': req.duration
                    }
                    
                    # Update schedules
                    self._allocate_slot(slot, req, room)
                    scheduled_classes.append(class_info)
                else:
                    # Log scheduling failure
                    print(f"Warning: Could not schedule {req.subject_name} for group {req.student_group_id}")
        
        return scheduled_classes
    
    async def _find_best_slot(
        self, 
        req: ClassRequirement,
        available_rooms: Dict[str, List[Dict]]
    ) -> Optional[Tuple[TimeSlot, Dict]]:
        """Find the best available time slot for a class using greedy heuristics"""
        
        candidate_slots = []
        rooms_of_type = available_rooms.get(req.room_type, [])
        
        if not rooms_of_type:
            return None
        
        # Generate all possible slots
        for day in range(self.days):
            for period in range(self.periods_per_day):
                slot = TimeSlot(day, period)
                
                # Check if duration fits
                if period + req.duration > self.periods_per_day:
                    continue
                
                # Try each room
                for room in rooms_of_type:
                    score = await self._evaluate_slot(slot, req, room)
                    
                    if score > 0:  # Valid slot
                        heapq.heappush(candidate_slots, (-score, slot, room))
        
        # Return best slot if available
        if candidate_slots:
            _, best_slot, best_room = heapq.heappop(candidate_slots)
            return (best_slot, best_room)
        
        return None
    
    async def _evaluate_slot(
        self,
        slot: TimeSlot,
        req: ClassRequirement,
        room: Dict
    ) -> float:
        """Evaluate how good a slot is for a requirement (higher score is better)"""
        
        # Start with base score
        score = 100.0
        
        # Check hard constraints (if violated, return 0)
        if not self._check_hard_constraints(slot, req, room):
            return 0
        
        # Soft constraint: Preferred slots
        if req.preferred_slots and slot in req.preferred_slots:
            score += 50
        
        # Soft constraint: Faculty preferences
        if req.faculty_id in self.constraints:
            constraint = self.constraints[req.faculty_id]
            
            # Preferred days bonus
            if constraint.preferred_days and slot.day in constraint.preferred_days:
                score += 20
            
            # Check consecutive hours
            consecutive_penalty = self._calculate_consecutive_penalty(slot, req.faculty_id, constraint)
            score -= consecutive_penalty
            
            # Check gap requirements
            gap_penalty = self._calculate_gap_penalty(slot, req.faculty_id, constraint)
            score -= gap_penalty
        
        # Green optimization: Minimize faculty movement
        movement_penalty = self._calculate_movement_penalty(slot, req.faculty_id, room)
        score -= movement_penalty
        
        # Fatigue optimization: Avoid heavy subjects in afternoon/evening
        if req.subject_name.lower() in ['mathematics', 'physics', 'chemistry']:
            if slot.period >= 5:  # After 2 PM
                score -= 30
        
        # Balance distribution across week
        day_load = len([s for s in self.group_schedule[req.student_group_id] if s.day == slot.day])
        if day_load > 4:  # Too many classes in one day
            score -= day_load * 10
        
        # Room capacity matching
        room_capacity = room.get('capacity', 100)
        # Ideally we'd check group size, but using a simple heuristic
        if room_capacity < 30:  # Small room
            score -= 10
        
        return max(0, score)
    
    def _check_hard_constraints(
        self,
        slot: TimeSlot,
        req: ClassRequirement,
        room: Dict
    ) -> bool:
        """Check if hard constraints are satisfied"""
        
        # Check if slot duration is available
        for i in range(req.duration):
            check_slot = TimeSlot(slot.day, slot.period + i)
            
            # Faculty availability
            if check_slot in self.faculty_schedule[req.faculty_id]:
                return False
            
            # Room availability
            if check_slot in self.room_schedule[room['room_id']]:
                return False
            
            # Student group availability
            if check_slot in self.group_schedule[req.student_group_id]:
                return False
            
            # Check faculty unavailability constraints
            if req.faculty_id in self.constraints:
                if check_slot in self.constraints[req.faculty_id].unavailable_slots:
                    return False
        
        return True
    
    def _calculate_consecutive_penalty(
        self,
        slot: TimeSlot,
        faculty_id: str,
        constraint: SchedulingConstraint
    ) -> float:
        """Calculate penalty for too many consecutive hours"""
        
        # Count consecutive hours before and after this slot
        consecutive = 1
        
        # Check before
        for i in range(1, constraint.max_consecutive_hours):
            check_slot = TimeSlot(slot.day, slot.period - i)
            if check_slot in self.faculty_schedule[faculty_id]:
                consecutive += 1
            else:
                break
        
        # Check after
        for i in range(1, constraint.max_consecutive_hours):
            check_slot = TimeSlot(slot.day, slot.period + i)
            if check_slot in self.faculty_schedule[faculty_id]:
                consecutive += 1
            else:
                break
        
        # Penalty if exceeds max consecutive hours
        if consecutive > constraint.max_consecutive_hours:
            return (consecutive - constraint.max_consecutive_hours) * 20
        
        return 0
    
    def _calculate_gap_penalty(
        self,
        slot: TimeSlot,
        faculty_id: str,
        constraint: SchedulingConstraint
    ) -> float:
        """Calculate penalty for not meeting gap requirements"""
        
        if constraint.min_gap_between_classes == 0:
            return 0
        
        # Find nearest class for this faculty on same day
        faculty_slots_today = [
            s for s in self.faculty_schedule[faculty_id] 
            if s.day == slot.day
        ]
        
        if not faculty_slots_today:
            return 0
        
        min_distance = float('inf')
        for existing_slot in faculty_slots_today:
            distance = abs(existing_slot.period - slot.period)
            min_distance = min(min_distance, distance)
        
        # Penalty if gap is too small
        if min_distance < constraint.min_gap_between_classes:
            return 15
        
        return 0
    
    def _calculate_movement_penalty(
        self,
        slot: TimeSlot,
        faculty_id: str,
        room: Dict
    ) -> float:
        """Calculate penalty for faculty movement between rooms"""
        
        # Find adjacent classes for this faculty
        prev_slot = TimeSlot(slot.day, slot.period - 1)
        next_slot = TimeSlot(slot.day, slot.period + 1)
        
        penalty = 0
        
        # Check if faculty has classes immediately before or after
        for existing_slot in self.faculty_schedule[faculty_id]:
            if existing_slot == prev_slot or existing_slot == next_slot:
                # Find room of existing class
                existing_room = self._get_room_for_slot(faculty_id, existing_slot)
                if existing_room and existing_room != room['room_id']:
                    penalty += 25  # Penalty for room change
        
        return penalty
    
    def _get_room_for_slot(self, faculty_id: str, slot: TimeSlot) -> Optional[str]:
        """Get room ID for a faculty's class at given slot"""
        # This would need to track room assignments
        # Simplified implementation
        return None
    
    def _allocate_slot(
        self,
        slot: TimeSlot,
        req: ClassRequirement,
        room: Dict
    ):
        """Allocate a time slot for a class"""
        
        # Mark slots as occupied for duration
        for i in range(req.duration):
            occupied_slot = TimeSlot(slot.day, slot.period + i)
            
            self.faculty_schedule[req.faculty_id].add(occupied_slot)
            self.room_schedule[room['room_id']].add(occupied_slot)
            self.group_schedule[req.student_group_id].add(occupied_slot)
    
    async def _generate_schedule_output(self, scheduled_classes: List[Dict]) -> Dict[str, Any]:
        """Generate final schedule output format"""
        
        schedule = {
            'weekly_schedule': {},
            'statistics': {},
            'conflicts': [],
            'utilization_rate': 0,
            'algorithm': 'Greedy'
        }
        
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        
        # Initialize days
        for day in days:
            schedule['weekly_schedule'][day] = {}
        
        # Populate schedule
        for class_info in scheduled_classes:
            day_name = days[class_info['day']]
            time_slot = class_info['time_slot']
            
            if time_slot not in schedule['weekly_schedule'][day_name]:
                schedule['weekly_schedule'][day_name][time_slot] = []
            
            schedule['weekly_schedule'][day_name][time_slot].append(class_info)
        
        # Calculate statistics
        total_slots = self.days * self.periods_per_day
        occupied_slots = len(scheduled_classes)
        schedule['statistics'] = {
            'total_classes_scheduled': len(scheduled_classes),
            'total_available_slots': total_slots,
            'utilization_rate': (occupied_slots / total_slots) * 100 if total_slots > 0 else 0
        }
        
        schedule['utilization_rate'] = schedule['statistics']['utilization_rate']
        
        # Add metadata
        schedule['subjects'] = list(set(c['subject_id'] for c in scheduled_classes))
        schedule['faculty'] = list(set(c['faculty_id'] for c in scheduled_classes))
        schedule['rooms'] = list(set(c['room_id'] for c in scheduled_classes))
        schedule['student_groups'] = list(set(c['student_group_id'] for c in scheduled_classes))
        
        return schedule