# conflict_resolver.py - Conflict Detection and Resolution System
from typing import Dict, List, Set, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict
import asyncio

@dataclass
class Conflict:
    """Represents a scheduling conflict"""
    conflict_id: str
    conflict_type: str  # faculty_overlap, room_booking, student_clash, capacity_exceeded
    severity: str  # critical, high, medium, low
    description: str
    affected_classes: List[Dict]
    resolution_suggestions: List[str]
    time_slot: str
    day: str

class ConflictResolver:
    """Detects and resolves scheduling conflicts"""
    
    def __init__(self):
        self.conflicts = []
        self.conflict_count = 0
        
    async def resolve_conflicts(self, schedule: Dict[str, Any]) -> Dict[str, Any]:
        """Main method to detect and resolve all conflicts"""
        
        # Detect all types of conflicts
        conflicts = await self._detect_all_conflicts(schedule)
        
        # Attempt automatic resolution
        if conflicts:
            schedule = await self._auto_resolve_conflicts(schedule, conflicts)
            
            # Re-check for remaining conflicts
            remaining_conflicts = await self._detect_all_conflicts(schedule)
            schedule['conflicts'] = remaining_conflicts
        else:
            schedule['conflicts'] = []
        
        return schedule
    
    async def _detect_all_conflicts(self, schedule: Dict[str, Any]) -> List[Conflict]:
        """Detect all types of conflicts in the schedule"""
        
        all_conflicts = []
        
        # Parallel conflict detection
        tasks = [
            self._detect_faculty_conflicts(schedule),
            self._detect_room_conflicts(schedule),
            self._detect_student_group_conflicts(schedule),
            self._detect_capacity_conflicts(schedule)
        ]
        
        results = await asyncio.gather(*tasks)
        
        for conflict_list in results:
            all_conflicts.extend(conflict_list)
        
        return all_conflicts
    
    async def _detect_faculty_conflicts(self, schedule: Dict[str, Any]) -> List[Conflict]:
        """Detect faculty double-booking conflicts"""
        
        conflicts = []
        faculty_schedule = defaultdict(list)
        
        # Build faculty schedule map
        for day, day_schedule in schedule.get('weekly_schedule', {}).items():
            for time_slot, classes in day_schedule.items():
                if isinstance(classes, list):
                    for class_info in classes:
                        faculty_id = class_info.get('faculty_id')
                        if faculty_id:
                            faculty_schedule[faculty_id].append({
                                'day': day,
                                'time_slot': time_slot,
                                'class_info': class_info
                            })
        
        # Check for overlaps
        for faculty_id, classes in faculty_schedule.items():
            # Group by day and time
            time_groups = defaultdict(list)
            for class_entry in classes:
                key = f"{class_entry['day']}_{class_entry['time_slot']}"
                time_groups[key].append(class_entry)
            
            # Find conflicts (more than one class at same time)
            for time_key, class_list in time_groups.items():
                if len(class_list) > 1:
                    day, time_slot = time_key.split('_', 1)
                    
                    conflict = Conflict(
                        conflict_id=f"faculty_conflict_{self.conflict_count}",
                        conflict_type="faculty_overlap",
                        severity="critical",
                        description=f"Faculty {faculty_id} has {len(class_list)} classes at the same time",
                        affected_classes=[c['class_info'] for c in class_list],
                        resolution_suggestions=[
                            "Reschedule one class to a different time slot",
                            "Assign alternative faculty member",
                            "Split class into multiple sections"
                        ],
                        time_slot=time_slot,
                        day=day
                    )
                    conflicts.append(conflict)
                    self.conflict_count += 1
        
        return conflicts
    
    async def _detect_room_conflicts(self, schedule: Dict[str, Any]) -> List[Conflict]:
        """Detect room double-booking conflicts"""
        
        conflicts = []
        room_schedule = defaultdict(list)
        
        # Build room schedule map
        for day, day_schedule in schedule.get('weekly_schedule', {}).items():
            for time_slot, classes in day_schedule.items():
                if isinstance(classes, list):
                    for class_info in classes:
                        room_id = class_info.get('room_id')
                        if room_id:
                            room_schedule[room_id].append({
                                'day': day,
                                'time_slot': time_slot,
                                'class_info': class_info
                            })
        
        # Check for overlaps
        for room_id, classes in room_schedule.items():
            # Group by day and time
            time_groups = defaultdict(list)
            for class_entry in classes:
                key = f"{class_entry['day']}_{class_entry['time_slot']}"
                time_groups[key].append(class_entry)
            
            # Find conflicts
            for time_key, class_list in time_groups.items():
                if len(class_list) > 1:
                    day, time_slot = time_key.split('_', 1)
                    
                    conflict = Conflict(
                        conflict_id=f"room_conflict_{self.conflict_count}",
                        conflict_type="room_booking",
                        severity="critical",
                        description=f"Room {room_id} booked for {len(class_list)} classes simultaneously",
                        affected_classes=[c['class_info'] for c in class_list],
                        resolution_suggestions=[
                            "Move one class to available room",
                            "Reschedule to different time slot",
                            "Use online/hybrid mode for one class"
                        ],
                        time_slot=time_slot,
                        day=day
                    )
                    conflicts.append(conflict)
                    self.conflict_count += 1
        
        return conflicts
    
    async def _detect_student_group_conflicts(self, schedule: Dict[str, Any]) -> List[Conflict]:
        """Detect student group scheduling conflicts"""
        
        conflicts = []
        group_schedule = defaultdict(list)
        
        # Build student group schedule map
        for day, day_schedule in schedule.get('weekly_schedule', {}).items():
            for time_slot, classes in day_schedule.items():
                if isinstance(classes, list):
                    for class_info in classes:
                        group_id = class_info.get('group_id') or class_info.get('student_group_id')
                        if group_id:
                            group_schedule[group_id].append({
                                'day': day,
                                'time_slot': time_slot,
                                'class_info': class_info
                            })
        
        # Check for overlaps
        for group_id, classes in group_schedule.items():
            # Group by day and time
            time_groups = defaultdict(list)
            for class_entry in classes:
                key = f"{class_entry['day']}_{class_entry['time_slot']}"
                time_groups[key].append(class_entry)
            
            # Find conflicts
            for time_key, class_list in time_groups.items():
                if len(class_list) > 1:
                    day, time_slot = time_key.split('_', 1)
                    
                    conflict = Conflict(
                        conflict_id=f"student_conflict_{self.conflict_count}",
                        conflict_type="student_clash",
                        severity="critical",
                        description=f"Student group {group_id} has {len(class_list)} classes at same time",
                        affected_classes=[c['class_info'] for c in class_list],
                        resolution_suggestions=[
                            "Reschedule one class to different slot",
                            "Create additional section for elective",
                            "Move to asynchronous/online mode"
                        ],
                        time_slot=time_slot,
                        day=day
                    )
                    conflicts.append(conflict)
                    self.conflict_count += 1
        
        return conflicts
    
    async def _detect_capacity_conflicts(self, schedule: Dict[str, Any]) -> List[Conflict]:
        """Detect room capacity vs student group size conflicts"""
        
        conflicts = []
        
        # This would need access to room capacities and group sizes
        # Mock implementation for demonstration
        
        return conflicts
    
    async def _auto_resolve_conflicts(
        self,
        schedule: Dict[str, Any],
        conflicts: List[Conflict]
    ) -> Dict[str, Any]:
        """Attempt to automatically resolve detected conflicts"""
        
        resolved_schedule = schedule.copy()
        
        # Sort conflicts by severity
        critical_conflicts = [c for c in conflicts if c.severity == "critical"]
        
        for conflict in critical_conflicts:
            if conflict.conflict_type == "faculty_overlap":
                resolved_schedule = await self._resolve_faculty_conflict(resolved_schedule, conflict)
            
            elif conflict.conflict_type == "room_booking":
                resolved_schedule = await self._resolve_room_conflict(resolved_schedule, conflict)
            
            elif conflict.conflict_type == "student_clash":
                resolved_schedule = await self._resolve_student_conflict(resolved_schedule, conflict)
        
        return resolved_schedule
    
    async def _resolve_faculty_conflict(
        self,
        schedule: Dict[str, Any],
        conflict: Conflict
    ) -> Dict[str, Any]:
        """Resolve faculty double-booking by rescheduling"""
        
        # Find alternative time slot for one of the conflicting classes
        affected_classes = conflict.affected_classes
        
        if len(affected_classes) < 2:
            return schedule
        
        # Try to move the lower priority class
        class_to_move = affected_classes[-1]  # Last class (assumed lower priority)
        
        # Find available slot
        available_slot = self._find_available_slot(schedule, class_to_move)
        
        if available_slot:
            # Remove from current slot
            self._remove_class_from_schedule(schedule, conflict.day, conflict.time_slot, class_to_move)
            
            # Add to new slot
            new_day, new_time = available_slot
            self._add_class_to_schedule(schedule, new_day, new_time, class_to_move)
        
        return schedule
    
    async def _resolve_room_conflict(
        self,
        schedule: Dict[str, Any],
        conflict: Conflict
    ) -> Dict[str, Any]:
        """Resolve room double-booking by finding alternative room"""
        
        affected_classes = conflict.affected_classes
        
        if len(affected_classes) < 2:
            return schedule
        
        # Try to find alternative room for one class
        class_to_reassign = affected_classes[-1]
        
        # Find available room at same time
        alternative_room = self._find_available_room(
            schedule,
            conflict.day,
            conflict.time_slot,
            class_to_reassign.get('room_type', 'lecture')
        )
        
        if alternative_room:
            # Update room assignment
            class_to_reassign['room_id'] = alternative_room
            class_to_reassign['room_name'] = f"Room {alternative_room}"
        
        return schedule
    
    async def _resolve_student_conflict(
        self,
        schedule: Dict[str, Any],
        conflict: Conflict
    ) -> Dict[str, Any]:
        """Resolve student group scheduling conflict"""
        
        # Similar to faculty conflict resolution
        return await self._resolve_faculty_conflict(schedule, conflict)
    
    def _find_available_slot(
        self,
        schedule: Dict[str, Any],
        class_info: Dict
    ) -> Tuple[str, str]:
        """Find an available time slot for a class"""
        
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        time_slots = [
            "09:00-10:00", "10:00-11:00", "11:00-12:00", "12:00-13:00",
            "14:00-15:00", "15:00-16:00", "16:00-17:00", "17:00-18:00"
        ]
        
        faculty_id = class_info.get('faculty_id')
        group_id = class_info.get('group_id') or class_info.get('student_group_id')
        
        for day in days:
            for time_slot in time_slots:
                if self._is_slot_available(schedule, day, time_slot, faculty_id, group_id):
                    return (day, time_slot)
        
        return None
    
    def _is_slot_available(
        self,
        schedule: Dict[str, Any],
        day: str,
        time_slot: str,
        faculty_id: str,
        group_id: str
    ) -> bool:
        """Check if a time slot is available for given faculty and group"""
        
        day_schedule = schedule.get('weekly_schedule', {}).get(day, {})
        slot_classes = day_schedule.get(time_slot, [])
        
        if not isinstance(slot_classes, list):
            slot_classes = [slot_classes] if slot_classes else []
        
        for class_info in slot_classes:
            if class_info.get('faculty_id') == faculty_id:
                return False
            if (class_info.get('group_id') == group_id or 
                class_info.get('student_group_id') == group_id):
                return False
        
        return True
    
    def _find_available_room(
        self,
        schedule: Dict[str, Any],
        day: str,
        time_slot: str,
        room_type: str
    ) -> str:
        """Find an available room at given time"""
        
    def _find_available_room(
        self,
        schedule: Dict[str, Any],
        day: str,
        time_slot: str,
        room_type: str
    ) -> str:
        """Find an available room at given time"""
        
        # Mock implementation - would need actual room database
        available_rooms = ['R101', 'R102', 'R103', 'L201', 'L202', 'L203']
        
        day_schedule = schedule.get('weekly_schedule', {}).get(day, {})
        slot_classes = day_schedule.get(time_slot, [])
        
        if not isinstance(slot_classes, list):
            slot_classes = [slot_classes] if slot_classes else []
        
        occupied_rooms = set(c.get('room_id') for c in slot_classes if c.get('room_id'))
        
        for room in available_rooms:
            if room not in occupied_rooms:
                return room
        
        return None
    
    def _remove_class_from_schedule(
        self,
        schedule: Dict[str, Any],
        day: str,
        time_slot: str,
        class_info: Dict
    ):
        """Remove a class from the schedule"""
        
        day_schedule = schedule.get('weekly_schedule', {}).get(day, {})
        slot_classes = day_schedule.get(time_slot, [])
        
        if isinstance(slot_classes, list):
            # Remove the specific class
            updated_classes = [c for c in slot_classes if c != class_info]
            schedule['weekly_schedule'][day][time_slot] = updated_classes
    
    def _add_class_to_schedule(
        self,
        schedule: Dict[str, Any],
        day: str,
        time_slot: str,
        class_info: Dict
    ):
        """Add a class to the schedule"""
        
        if day not in schedule.get('weekly_schedule', {}):
            schedule['weekly_schedule'][day] = {}
        
        if time_slot not in schedule['weekly_schedule'][day]:
            schedule['weekly_schedule'][day][time_slot] = []
        
        if not isinstance(schedule['weekly_schedule'][day][time_slot], list):
            schedule['weekly_schedule'][day][time_slot] = [schedule['weekly_schedule'][day][time_slot]]
        
        schedule['weekly_schedule'][day][time_slot].append(class_info)
    
    def generate_conflict_heatmap(self, schedule: Dict[str, Any]) -> Dict[str, Any]:
        """Generate conflict heatmap for visualization"""
        
        heatmap = {}
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        
        for day in days:
            day_conflicts = 0
            day_schedule = schedule.get('weekly_schedule', {}).get(day, {})
            
            for time_slot, classes in day_schedule.items():
                if isinstance(classes, list) and len(classes) > 1:
                    # Check for actual conflicts
                    faculty_ids = [c.get('faculty_id') for c in classes if c.get('faculty_id')]
                    room_ids = [c.get('room_id') for c in classes if c.get('room_id')]
                    
                    if len(faculty_ids) != len(set(faculty_ids)):
                        day_conflicts += 1
                    if len(room_ids) != len(set(room_ids)):
                        day_conflicts += 1
            
            # Categorize conflict level
            if day_conflicts == 0:
                level = "low"
            elif day_conflicts <= 2:
                level = "medium"
            else:
                level = "high"
            
            heatmap[day] = {
                "level": level,
                "conflicts": day_conflicts
            }
        
        return heatmap