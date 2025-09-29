# nep_compliance.py - NEP 2020 Compliance Verification System
from typing import Dict, List, Any
from dataclasses import dataclass
import asyncio

@dataclass
class NEPRequirement:
    """NEP 2020 requirement specification"""
    category: str
    min_percentage: float
    max_percentage: float
    min_credits: int
    description: str

class NEPComplianceChecker:
    """Verify NEP 2020 compliance for timetables"""
    
    def __init__(self):
        # NEP 2020 requirements for Four-Year Undergraduate Programme (FYUP)
        self.nep_requirements = {
            'major': NEPRequirement(
                category='major',
                min_percentage=40,
                max_percentage=50,
                min_credits=64,
                description='Major discipline courses'
            ),
            'minor': NEPRequirement(
                category='minor',
                min_percentage=20,
                max_percentage=30,
                min_credits=32,
                description='Minor discipline courses'
            ),
            'skill': NEPRequirement(
                category='skill',
                min_percentage=10,
                max_percentage=20,
                min_credits=16,
                description='Skill-based courses'
            ),
            'ability_enhancement': NEPRequirement(
                category='ability_enhancement',
                min_percentage=8,
                max_percentage=15,
                min_credits=12,
                description='Ability Enhancement Courses'
            ),
            'value_added': NEPRequirement(
                category='value_added',
                min_percentage=5,
                max_percentage=15,
                min_credits=8,
                description='Value-Added Courses'
            )
        }
        
        # B.Ed. and M.Ed. requirements
        self.teacher_education_requirements = {
            'pedagogy': 30,  # minimum percentage
            'subject_knowledge': 40,
            'practicum': 20,
            'electives': 10
        }
    
    async def check_compliance(self, schedule: Dict[str, Any]) -> Dict[str, Any]:
        """Main method to check NEP 2020 compliance"""
        
        compliance_report = {
            'overall_compliant': True,
            'compliance_score': 0,
            'category_compliance': {},
            'violations': [],
            'recommendations': [],
            'credit_distribution': {},
            'multidisciplinary_score': 0
        }
        
        # Extract schedule metadata
        program_type = schedule.get('program_type', 'FYUP')
        
        if program_type in ['FYUP', 'ITEP']:
            compliance_report = await self._check_fyup_compliance(schedule, compliance_report)
        elif program_type in ['B.Ed.', 'M.Ed.']:
            compliance_report = await self._check_teacher_education_compliance(schedule, compliance_report)
        
        # Calculate overall compliance score
        compliance_report['compliance_score'] = self._calculate_overall_score(compliance_report)
        
        return compliance_report
    
    async def _check_fyup_compliance(
        self,
        schedule: Dict[str, Any],
        report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check compliance for Four-Year Undergraduate Programme"""
        
        # Extract course distribution
        course_distribution = await self._analyze_course_distribution(schedule)
        
        # Check each NEP category
        for category, requirement in self.nep_requirements.items():
            category_data = course_distribution.get(category, {})
            percentage = category_data.get('percentage', 0)
            credits = category_data.get('credits', 0)
            
            is_compliant = (
                percentage >= requirement.min_percentage and
                percentage <= requirement.max_percentage and
                credits >= requirement.min_credits
            )
            
            report['category_compliance'][category] = {
                'compliant': is_compliant,
                'current_percentage': percentage,
                'required_range': f"{requirement.min_percentage}-{requirement.max_percentage}%",
                'current_credits': credits,
                'minimum_credits': requirement.min_credits,
                'description': requirement.description
            }
            
            # Add violations if not compliant
            if not is_compliant:
                report['overall_compliant'] = False
                
                if percentage < requirement.min_percentage:
                    report['violations'].append(
                        f"{category.title()} courses are below minimum requirement "
                        f"({percentage:.1f}% < {requirement.min_percentage}%)"
                    )
                    report['recommendations'].append(
                        f"Increase {category} course allocation by "
                        f"{requirement.min_percentage - percentage:.1f}%"
                    )
                
                if percentage > requirement.max_percentage:
                    report['violations'].append(
                        f"{category.title()} courses exceed maximum limit "
                        f"({percentage:.1f}% > {requirement.max_percentage}%)"
                    )
                    report['recommendations'].append(
                        f"Reduce {category} course allocation by "
                        f"{percentage - requirement.max_percentage:.1f}%"
                    )
                
                if credits < requirement.min_credits:
                    report['violations'].append(
                        f"{category.title()} credits are insufficient "
                        f"({credits} < {requirement.min_credits})"
                    )
                    report['recommendations'].append(
                        f"Add {requirement.min_credits - credits} more credits "
                        f"in {category} courses"
                    )
        
        # Check multidisciplinary requirement
        report['multidisciplinary_score'] = await self._calculate_multidisciplinary_score(schedule)
        
        if report['multidisciplinary_score'] < 70:
            report['violations'].append(
                f"Multidisciplinary exposure is low ({report['multidisciplinary_score']:.1f}%)"
            )
            report['recommendations'].append(
                "Increase interdisciplinary course offerings across different faculties"
            )
        
        # Check theory-practical balance
        theory_practical_ratio = await self._check_theory_practical_balance(schedule)
        report['credit_distribution'] = theory_practical_ratio
        
        if theory_practical_ratio['practical_percentage'] < 20:
            report['recommendations'].append(
                "Increase practical/lab components to at least 20% of total hours"
            )
        
        return report
    
    async def _check_teacher_education_compliance(
        self,
        schedule: Dict[str, Any],
        report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check compliance for B.Ed. and M.Ed. programs"""
        
        course_distribution = await self._analyze_teacher_education_distribution(schedule)
        
        for category, min_percentage in self.teacher_education_requirements.items():
            current_percentage = course_distribution.get(category, 0)
            
            is_compliant = current_percentage >= min_percentage
            
            report['category_compliance'][category] = {
                'compliant': is_compliant,
                'current_percentage': current_percentage,
                'minimum_percentage': min_percentage
            }
            
            if not is_compliant:
                report['overall_compliant'] = False
                report['violations'].append(
                    f"{category.title()} component is below minimum "
                    f"({current_percentage:.1f}% < {min_percentage}%)"
                )
                report['recommendations'].append(
                    f"Increase {category} courses by {min_percentage - current_percentage:.1f}%"
                )
        
        # Check teaching practice hours
        practicum_hours = course_distribution.get('practicum_hours', 0)
        if practicum_hours < 100:  # Minimum 100 hours of teaching practice
            report['violations'].append(
                f"Teaching practice hours insufficient ({practicum_hours} < 100 hours)"
            )
            report['recommendations'].append(
                f"Add {100 - practicum_hours} more hours of teaching practice"
            )
        
        return report
    
    async def _analyze_course_distribution(self, schedule: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze distribution of courses across NEP categories"""
        
        distribution = {}
        total_credits = 0
        
        # Count courses and credits by category
        category_counts = {
            'major': {'courses': 0, 'credits': 0},
            'minor': {'courses': 0, 'credits': 0},
            'skill': {'courses': 0, 'credits': 0},
            'ability_enhancement': {'courses': 0, 'credits': 0},
            'value_added': {'courses': 0, 'credits': 0}
        }
        
        # Parse subjects from schedule
        subjects = schedule.get('subjects', [])
        
        for subject in subjects:
            subject_type = subject.get('type', '').lower()
            credits = subject.get('credits', 3)
            
            if subject_type in category_counts:
                category_counts[subject_type]['courses'] += 1
                category_counts[subject_type]['credits'] += credits
                total_credits += credits
        
        # Calculate percentages
        for category, data in category_counts.items():
            percentage = (data['credits'] / total_credits * 100) if total_credits > 0 else 0
            distribution[category] = {
                'courses': data['courses'],
                'credits': data['credits'],
                'percentage': percentage
            }
        
        return distribution
    
    async def _analyze_teacher_education_distribution(self, schedule: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze distribution for teacher education programs"""
        
        distribution = {
            'pedagogy': 0,
            'subject_knowledge': 0,
            'practicum': 0,
            'electives': 0,
            'practicum_hours': 0
        }
        
        subjects = schedule.get('subjects', [])
        total_courses = len(subjects)
        
        if total_courses == 0:
            return distribution
        
        for subject in subjects:
            subject_type = subject.get('type', '').lower()
            
            if 'pedagogy' in subject_type or 'teaching' in subject_type:
                distribution['pedagogy'] += 1
            elif 'practical' in subject_type or 'practicum' in subject_type:
                distribution['practicum'] += 1
                distribution['practicum_hours'] += subject.get('practical_hours', 20)
            elif 'elective' in subject_type:
                distribution['electives'] += 1
            else:
                distribution['subject_knowledge'] += 1
        
        # Convert to percentages
        for key in ['pedagogy', 'subject_knowledge', 'practicum', 'electives']:
            distribution[key] = (distribution[key] / total_courses * 100)
        
        return distribution
    
    async def _calculate_multidisciplinary_score(self, schedule: Dict[str, Any]) -> float:
        """Calculate multidisciplinary exposure score"""
        
        subjects = schedule.get('subjects', [])
        
        if not subjects:
            return 0
        
        # Count unique departments/disciplines
        disciplines = set()
        for subject in subjects:
            department = subject.get('department', 'general')
            disciplines.add(department)
        
        # More disciplines = higher multidisciplinary score
        # Normalized score: 3+ disciplines = 100%, 2 = 70%, 1 = 40%
        if len(disciplines) >= 3:
            return 100
        elif len(disciplines) == 2:
            return 70
        elif len(disciplines) == 1:
            return 40
        
        return 0
    
    async def _check_theory_practical_balance(self, schedule: Dict[str, Any]) -> Dict[str, Any]:
        """Check theory-practical balance in curriculum"""
        
        subjects = schedule.get('subjects', [])
        
        total_theory_hours = 0
        total_practical_hours = 0
        total_internship_hours = 0
        
        for subject in subjects:
            total_theory_hours += subject.get('theory_hours', 0)
            total_practical_hours += subject.get('practical_hours', 0)
            
            # Check for internship/project components
            if 'internship' in subject.get('type', '').lower():
                total_internship_hours += subject.get('hours', 0)
        
        total_hours = total_theory_hours + total_practical_hours + total_internship_hours
        
        if total_hours == 0:
            return {
                'theory_percentage': 0,
                'practical_percentage': 0,
                'internship_percentage': 0
            }
        
        return {
            'theory_percentage': (total_theory_hours / total_hours) * 100,
            'practical_percentage': (total_practical_hours / total_hours) * 100,
            'internship_percentage': (total_internship_hours / total_hours) * 100,
            'theory_hours': total_theory_hours,
            'practical_hours': total_practical_hours,
            'internship_hours': total_internship_hours,
            'total_hours': total_hours
        }
    
    def _calculate_overall_score(self, report: Dict[str, Any]) -> float:
        """Calculate overall compliance score"""
        
        compliant_categories = sum(
            1 for cat in report['category_compliance'].values() 
            if cat.get('compliant', False)
        )
        
        total_categories = len(report['category_compliance'])
        
        if total_categories == 0:
            return 0
        
        base_score = (compliant_categories / total_categories) * 100
        
        # Bonus for multidisciplinary score
        multidisciplinary_bonus = report.get('multidisciplinary_score', 0) * 0.1
        
        # Penalty for violations
        violation_penalty = len(report.get('violations', [])) * 5
        
        final_score = min(100, max(0, base_score + multidisciplinary_bonus - violation_penalty))
        
        return round(final_score, 2)
    
    def generate_compliance_summary(self, compliance_report: Dict[str, Any]) -> str:
        """Generate human-readable compliance summary"""
        
        summary = f"NEP 2020 Compliance Report\n"
        summary += f"{'=' * 50}\n\n"
        
        summary += f"Overall Compliance: {'✓ COMPLIANT' if compliance_report['overall_compliant'] else '✗ NON-COMPLIANT'}\n"
        summary += f"Compliance Score: {compliance_report['compliance_score']:.1f}%\n"
        summary += f"Multidisciplinary Score: {compliance_report.get('multidisciplinary_score', 0):.1f}%\n\n"
        
        summary += "Category-wise Compliance:\n"
        summary += "-" * 50 + "\n"
        
        for category, data in compliance_report['category_compliance'].items():
            status = "✓" if data['compliant'] else "✗"
            summary += f"{status} {category.title()}: {data.get('current_percentage', 0):.1f}% "
            summary += f"(Required: {data.get('required_range', 'N/A')})\n"
        
        if compliance_report.get('violations'):
            summary += f"\nViolations ({len(compliance_report['violations'])}):\n"
            summary += "-" * 50 + "\n"
            for i, violation in enumerate(compliance_report['violations'], 1):
                summary += f"{i}. {violation}\n"
        
        if compliance_report.get('recommendations'):
            summary += f"\nRecommendations:\n"
            summary += "-" * 50 + "\n"
            for i, recommendation in enumerate(compliance_report['recommendations'], 1):
                summary += f"{i}. {recommendation}\n"
        
        # Credit distribution
        if compliance_report.get('credit_distribution'):
            summary += f"\nCredit Distribution:\n"
            summary += "-" * 50 + "\n"
            dist = compliance_report['credit_distribution']
            summary += f"Theory: {dist.get('theory_percentage', 0):.1f}%\n"
            summary += f"Practical: {dist.get('practical_percentage', 0):.1f}%\n"
            summary += f"Internship: {dist.get('internship_percentage', 0):.1f}%\n"
        
        return summary