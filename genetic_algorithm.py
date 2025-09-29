# genetic_algorithm.py - Genetic Algorithm for Timetable Optimization
import random
import numpy as np
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass
import asyncio
from concurrent.futures import ThreadPoolExecutor
import copy

@dataclass
class Gene:
    """Represents a single time slot assignment"""
    subject_id: str
    faculty_id: str
    room_id: str
    student_group_id: str
    day: int  # 0-4 (Monday-Friday)
    time_slot: int  # 0-7 (time slots in a day)
    
@dataclass
class Chromosome:
    """Represents a complete timetable solution"""
    genes: List[Gene]
    fitness_score: float = 0.0
    conflict_count: int = 0
    utilization_score: float = 0.0
    green_score: float = 0.0
    fatigue_score: float = 0.0

class GeneticScheduler:
    def __init__(self):
        self.population_size = 50
        self.generations = 100
        self.mutation_rate = 0.1
        self.crossover_rate = 0.8
        self.elite_percentage = 0.2
        
    async def optimize_schedule(self, initial_schedule: Dict[str, Any], optimization_level: str = "high"):
        """Main genetic algorithm optimization process"""
        
        # Set parameters based on optimization level
        self._set_optimization_parameters(optimization_level)
        
        # Initialize population with the greedy solution as seed
        population = await self._initialize_population(initial_schedule)
        
        best_solution = None
        best_fitness = float('-inf')
        
        for generation in range(self.generations):
            # Evaluate fitness for all chromosomes
            await self._evaluate_population_fitness(population)
            
            # Find best solution in current generation
            current_best = max(population, key=lambda x: x.fitness_score)
            if current_best.fitness_score > best_fitness:
                best_fitness = current_best.fitness_score
                best_solution = copy.deepcopy(current_best)
            
            # Create next generation
            population = await self._create_next_generation(population)
            
            # Early stopping if optimal solution found
            if best_fitness >= 99.0:  # Near-perfect solution
                break
                
        return await self._chromosome_to_schedule(best_solution)
    
    def _set_optimization_parameters(self, level: str):
        """Set GA parameters based on optimization level"""
        if level == "high":
            self.generations = 150
            self.population_size = 100
            self.mutation_rate = 0.05
        elif level == "medium":
            self.generations = 100
            self.population_size = 50
            self.mutation_rate = 0.1
        else:  # low
            self.generations = 50
            self.population_size = 30
            self.mutation_rate = 0.2
    
    async def _initialize_population(self, initial_schedule: Dict[str, Any]) -> List[Chromosome]:
        """Initialize population with diverse solutions"""
        population = []
        
        # Convert initial schedule to chromosome
        base_chromosome = await self._schedule_to_chromosome(initial_schedule)
        population.append(base_chromosome)
        
        # Generate diverse population through mutations and random generation
        for _ in range(self.population_size - 1):
            if random.random() < 0.5:
                # Create mutated version of base solution
                new_chromosome = copy.deepcopy(base_chromosome)
                await self._mutate_chromosome(new_chromosome, rate=0.3)
            else:
                # Create random solution
                new_chromosome = await self._generate_random_chromosome(initial_schedule)
            
            population.append(new_chromosome)
            
        return population
    
    async def _schedule_to_chromosome(self, schedule: Dict[str, Any]) -> Chromosome:
        """Convert schedule dictionary to chromosome representation"""
        genes = []
        
        for day_name, day_schedule in schedule.get('weekly_schedule', {}).items():
            day_idx = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'].index(day_name.lower())
            
            for time_slot, classes in day_schedule.items():
                slot_idx = self._time_to_slot_index(time_slot)
                
                if isinstance(classes, list):
                    for class_info in classes:
                        gene = Gene(
                            subject_id=class_info.get('subject_id', ''),
                            faculty_id=class_info.get('faculty_id', ''),
                            room_id=class_info.get('room_id', ''),
                            student_group_id=class_info.get('group_id', ''),
                            day=day_idx,
                            time_slot=slot_idx
                        )
                        genes.append(gene)
        
        return Chromosome(genes=genes)
    
    async def _generate_random_chromosome(self, schedule_template: Dict[str, Any]) -> Chromosome:
        """Generate a random chromosome for population diversity"""
        genes = []
        
        # Get available resources
        subjects = schedule_template.get('subjects', [])
        faculty = schedule_template.get('faculty', [])
        rooms = schedule_template.get('rooms', [])
        groups = schedule_template.get('student_groups', [])
        
        # Generate random assignments
        for _ in range(len(subjects) * 3):  # Approximate number of classes
            gene = Gene(
                subject_id=random.choice(subjects).get('id', '') if subjects else '',
                faculty_id=random.choice(faculty).get('id', '') if faculty else '',
                room_id=random.choice(rooms).get('id', '') if rooms else '',
                student_group_id=random.choice(groups).get('id', '') if groups else '',
                day=random.randint(0, 4),
                time_slot=random.randint(0, 7)
            )
            genes.append(gene)
        
        return Chromosome(genes=genes)
    
    async def _evaluate_population_fitness(self, population: List[Chromosome]):
        """Evaluate fitness for entire population using parallel processing"""
        with ThreadPoolExecutor(max_workers=4) as executor:
            fitness_tasks = [
                executor.submit(self._calculate_fitness, chromosome) 
                for chromosome in population
            ]
            
            for i, task in enumerate(fitness_tasks):
                fitness_result = task.result()
                population[i].fitness_score = fitness_result['total_score']
                population[i].conflict_count = fitness_result['conflicts']
                population[i].utilization_score = fitness_result['utilization']
                population[i].green_score = fitness_result['green_score']
                population[i].fatigue_score = fitness_result['fatigue_score']
    
    def _calculate_fitness(self, chromosome: Chromosome) -> Dict[str, float]:
        """Calculate comprehensive fitness score for a chromosome"""
        
        # 1. Conflict Analysis (40% weight)
        conflict_score = self._evaluate_conflicts(chromosome)
        
        # 2. Resource Utilization (25% weight)
        utilization_score = self._evaluate_utilization(chromosome)
        
        # 3. Green Optimization - Movement Minimization (20% weight)
        green_score = self._evaluate_green_optimization(chromosome)
        
        # 4. Fatigue-Free Scheduling (15% weight)
        fatigue_score = self._evaluate_fatigue_prevention(chromosome)
        
        # Weighted total score
        total_score = (
            conflict_score * 0.40 +
            utilization_score * 0.25 +
            green_score * 0.20 +
            fatigue_score * 0.15
        )
        
        return {
            'total_score': total_score,
            'conflicts': 100 - conflict_score,
            'utilization': utilization_score,
            'green_score': green_score,
            'fatigue_score': fatigue_score
        }
    
    def _evaluate_conflicts(self, chromosome: Chromosome) -> float:
        """Evaluate and penalize scheduling conflicts"""
        conflicts = 0
        faculty_schedule = {}
        room_schedule = {}
        student_schedule = {}
        
        for gene in chromosome.genes:
            time_key = f"{gene.day}_{gene.time_slot}"
            
            # Faculty conflict check
            if gene.faculty_id in faculty_schedule:
                if time_key in faculty_schedule[gene.faculty_id]:
                    conflicts += 1
                else:
                    faculty_schedule[gene.faculty_id].add(time_key)
            else:
                faculty_schedule[gene.faculty_id] = {time_key}
            
            # Room conflict check
            if gene.room_id in room_schedule:
                if time_key in room_schedule[gene.room_id]:
                    conflicts += 1
                else:
                    room_schedule[gene.room_id].add(time_key)
            else:
                room_schedule[gene.room_id] = {time_key}
            
            # Student group conflict check
            if gene.student_group_id in student_schedule:
                if time_key in student_schedule[gene.student_group_id]:
                    conflicts += 1
                else:
                    student_schedule[gene.student_group_id].add(time_key)
            else:
                student_schedule[gene.student_group_id] = {time_key}
        
        # Convert conflicts to score (0-100, higher is better)
        max_possible_conflicts = len(chromosome.genes)
        if max_possible_conflicts == 0:
            return 100
        
        conflict_percentage = (conflicts / max_possible_conflicts) * 100
        return max(0, 100 - conflict_percentage * 2)  # Heavy penalty for conflicts
    
    def _evaluate_utilization(self, chromosome: Chromosome) -> float:
        """Evaluate resource utilization efficiency"""
        if not chromosome.genes:
            return 0
        
        # Calculate faculty utilization
        faculty_hours = {}
        room_hours = {}
        
        for gene in chromosome.genes:
            faculty_hours[gene.faculty_id] = faculty_hours.get(gene.faculty_id, 0) + 1
            room_hours[gene.room_id] = room_hours.get(gene.room_id, 0) + 1
        
        # Ideal utilization ranges
        ideal_faculty_hours = 6  # 6 hours per day average
        ideal_room_hours = 7     # 7 hours per day average
        
        faculty_utilization = []
        for hours in faculty_hours.values():
            if hours == 0:
                utilization = 0
            else:
                utilization = min(100, (hours / ideal_faculty_hours) * 100)
                # Penalty for over-utilization
                if hours > ideal_faculty_hours:
                    utilization = max(0, 100 - (hours - ideal_faculty_hours) * 10)
            faculty_utilization.append(utilization)
        
        room_utilization = []
        for hours in room_hours.values():
            if hours == 0:
                utilization = 0
            else:
                utilization = min(100, (hours / ideal_room_hours) * 100)
            room_utilization.append(utilization)
        
        # Average utilization score
        avg_faculty_util = np.mean(faculty_utilization) if faculty_utilization else 0
        avg_room_util = np.mean(room_utilization) if room_utilization else 0
        
        return (avg_faculty_util + avg_room_util) / 2
    
    def _evaluate_green_optimization(self, chromosome: Chromosome) -> float:
        """Evaluate movement minimization for faculty (Green Timetable)"""
        if not chromosome.genes:
            return 100
        
        faculty_movements = {}
        
        # Group genes by faculty and day
        faculty_daily_schedule = {}
        for gene in chromosome.genes:
            if gene.faculty_id not in faculty_daily_schedule:
                faculty_daily_schedule[gene.faculty_id] = {}
            if gene.day not in faculty_daily_schedule[gene.faculty_id]:
                faculty_daily_schedule[gene.faculty_id][gene.day] = []
            faculty_daily_schedule[gene.faculty_id][gene.day].append(gene)
        
        total_movements = 0
        total_possible_movements = 0
        
        for faculty_id, daily_schedule in faculty_daily_schedule.items():
            for day, day_genes in daily_schedule.items():
                if len(day_genes) <= 1:
                    continue
                
                # Sort by time slot
                day_genes.sort(key=lambda x: x.time_slot)
                
                # Count room changes (movements)
                movements = 0
                for i in range(len(day_genes) - 1):
                    if day_genes[i].room_id != day_genes[i + 1].room_id:
                        movements += 1
                
                total_movements += movements
                total_possible_movements += len(day_genes) - 1
        
        if total_possible_movements == 0:
            return 100
        
        # Calculate movement reduction percentage
        movement_rate = total_movements / total_possible_movements
        return max(0, 100 - (movement_rate * 100))
    
    def _evaluate_fatigue_prevention(self, chromosome: Chromosome) -> float:
        """Evaluate fatigue-free scheduling (no back-to-back heavy subjects)"""
        if not chromosome.genes:
            return 100
        
        # Define heavy subjects (this would come from configuration)
        heavy_subjects = {'mathematics', 'physics', 'chemistry', 'advanced_math'}
        
        fatigue_violations = 0
        total_checks = 0
        
        # Group by student groups and days
        group_daily_schedule = {}
        for gene in chromosome.genes:
            if gene.student_group_id not in group_daily_schedule:
                group_daily_schedule[gene.student_group_id] = {}
            if gene.day not in group_daily_schedule[gene.student_group_id]:
                group_daily_schedule[gene.student_group_id][gene.day] = []
            group_daily_schedule[gene.student_group_id][gene.day].append(gene)
        
        for group_id, daily_schedule in group_daily_schedule.items():
            for day, day_genes in daily_schedule.items():
                if len(day_genes) <= 1:
                    continue
                
                # Sort by time slot
                day_genes.sort(key=lambda x: x.time_slot)
                
                # Check for back-to-back heavy subjects
                for i in range(len(day_genes) - 1):
                    current_subject = day_genes[i].subject_id.lower()
                    next_subject = day_genes[i + 1].subject_id.lower()
                    
                    # Check if consecutive time slots
                    if day_genes[i + 1].time_slot == day_genes[i].time_slot + 1:
                        total_checks += 1
                        if (current_subject in heavy_subjects and 
                            next_subject in heavy_subjects):
                            fatigue_violations += 1
        
        if total_checks == 0:
            return 100
        
        fatigue_rate = fatigue_violations / total_checks
        return max(0, 100 - (fatigue_rate * 100))
    
    async def _create_next_generation(self, population: List[Chromosome]) -> List[Chromosome]:
        """Create next generation using selection, crossover, and mutation"""
        # Sort population by fitness
        population.sort(key=lambda x: x.fitness_score, reverse=True)
        
        new_population = []
        elite_count = int(self.population_size * self.elite_percentage)
        
        # Elitism - keep best solutions
        new_population.extend(population[:elite_count])
        
        # Generate remaining population through crossover and mutation
        while len(new_population) < self.population_size:
            # Tournament selection
            parent1 = self._tournament_selection(population)
            parent2 = self._tournament_selection(population)
            
            # Crossover
            if random.random() < self.crossover_rate:
                child1, child2 = await self._crossover(parent1, parent2)
            else:
                child1, child2 = copy.deepcopy(parent1), copy.deepcopy(parent2)
            
            # Mutation
            if random.random() < self.mutation_rate:
                await self._mutate_chromosome(child1)
            if random.random() < self.mutation_rate:
                await self._mutate_chromosome(child2)
            
            new_population.extend([child1, child2])
        
        # Trim to exact population size
        return new_population[:self.population_size]
    
    def _tournament_selection(self, population: List[Chromosome], tournament_size: int = 5) -> Chromosome:
        """Tournament selection for parent selection"""
        tournament = random.sample(population, min(tournament_size, len(population)))
        return max(tournament, key=lambda x: x.fitness_score)
    
    async def _crossover(self, parent1: Chromosome, parent2: Chromosome) -> Tuple[Chromosome, Chromosome]:
        """Single-point crossover between two chromosomes"""
        if not parent1.genes or not parent2.genes:
            return copy.deepcopy(parent1), copy.deepcopy(parent2)
        
        # Find crossover point
        min_length = min(len(parent1.genes), len(parent2.genes))
        crossover_point = random.randint(1, min_length - 1)
        
        # Create children
        child1_genes = parent1.genes[:crossover_point] + parent2.genes[crossover_point:]
        child2_genes = parent2.genes[:crossover_point] + parent1.genes[crossover_point:]
        
        child1 = Chromosome(genes=child1_genes)
        child2 = Chromosome(genes=child2_genes)
        
        return child1, child2
    
    async def _mutate_chromosome(self, chromosome: Chromosome, rate: float = None):
        """Mutate chromosome by randomly changing gene properties"""
        if not chromosome.genes:
            return
        
        mutation_rate = rate if rate is not None else self.mutation_rate
        
        for gene in chromosome.genes:
            if random.random() < mutation_rate:
                # Randomly choose what to mutate
                mutation_type = random.choice(['day', 'time_slot', 'room_id'])
                
                if mutation_type == 'day':
                    gene.day = random.randint(0, 4)
                elif mutation_type == 'time_slot':
                    gene.time_slot = random.randint(0, 7)
                elif mutation_type == 'room_id':
                    # This would need access to available rooms
                    # For now, just modify slightly
                    pass
    
    async def _chromosome_to_schedule(self, chromosome: Chromosome) -> Dict[str, Any]:
        """Convert chromosome back to schedule format"""
        schedule = {
            'weekly_schedule': {},
            'optimization_metrics': {
                'fitness_score': chromosome.fitness_score,
                'conflict_count': chromosome.conflict_count,
                'utilization_rate': chromosome.utilization_score,
                'movement_reduction': chromosome.green_score,
                'fatigue_prevention': chromosome.fatigue_score
            },
            'ai_metadata': {
                'algorithm': 'Genetic Algorithm',
                'generations_used': self.generations,
                'population_size': self.population_size,
                'final_conflicts': chromosome.conflict_count
            }
        }
        
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        
        # Initialize days
        for day in days:
            schedule['weekly_schedule'][day] = {}
        
        # Populate schedule from genes
        for gene in chromosome.genes:
            day_name = days[gene.day]
            time_slot = self._slot_index_to_time(gene.time_slot)
            
            if time_slot not in schedule['weekly_schedule'][day_name]:
                schedule['weekly_schedule'][day_name][time_slot] = []
            
            class_info = {
                'subject_id': gene.subject_id,
                'faculty_id': gene.faculty_id,
                'room_id': gene.room_id,
                'group_id': gene.student_group_id
            }
            
            schedule['weekly_schedule'][day_name][time_slot].append(class_info)
        
        return schedule
    
    def _time_to_slot_index(self, time_str: str) -> int:
        """Convert time string to slot index"""
        time_slots = [
            "09:00-10:00", "10:00-11:00", "11:00-12:00", "12:00-13:00",
            "14:00-15:00", "15:00-16:00", "16:00-17:00", "17:00-18:00"
        ]
        try:
            return time_slots.index(time_str)
        except ValueError:
            return 0
    
    def _slot_index_to_time(self, index: int) -> str:
        """Convert slot index to time string"""
        time_slots = [
            "09:00-10:00", "10:00-11:00", "11:00-12:00", "12:00-13:00",
            "14:00-15:00", "15:00-16:00", "16:00-17:00", "17:00-18:00"
        ]
        return time_slots[min(index, len(time_slots) - 1)]