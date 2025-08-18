from langchain_openai import ChatOpenAI
from crewai import Agent, Task, Crew, Process
import os
from dotenv import load_dotenv
from crewai_tools import SerperDevTool
from datetime import datetime
import yaml

load_dotenv()

class TripPlanner:
    def __init__(self, start_location, destination, num_people, budget_range, budget, duration, interests):
        self.start_location = start_location
        self.destination = destination
        self.num_people = int(num_people)
        self.budget_range = budget_range  # low, mid, high
        self.budget = int(budget)
        self.duration = duration
        self.interests = interests
        
        # Initialize LLM and tools
        self.llm = ChatOpenAI(
            model="gpt-4-turbo",
            verbose=True,
            temperature=0.5,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.search_tool = SerperDevTool()
        
        # Set budget allocations based on range
        self._set_budget_allocations()
        
    def _set_budget_allocations(self):
        """Set budget allocations based on the selected range"""
        if self.budget_range == 'low':
            self.transport_ratio = 0.2
            self.accommodation_ratio = 0.2
            self.food_ratio = 0.15
            self.activities_ratio = 0.35
            self.misc_ratio = 0.05
        elif self.budget_range == 'mid':
            self.transport_ratio = 0.25
            self.accommodation_ratio = 0.25
            self.food_ratio = 0.25
            self.activities_ratio = 0.20
            self.misc_ratio = 0.05
        else:  # high
            self.transport_ratio = 0.25
            self.accommodation_ratio = 0.25
            self.food_ratio = 0.25
            self.activities_ratio = 0.20
            self.misc_ratio = 0.05
            
        # Calculate actual amounts
        self.transport_budget = int(self.budget * self.transport_ratio)
        self.accommodation_budget = int(self.budget * self.accommodation_ratio)
        self.food_budget = int(self.budget * self.food_ratio)
        self.activities_budget = int(self.budget * self.activities_ratio)
        self.misc_budget = self.budget - (self.transport_budget + self.accommodation_budget + 
                                        self.food_budget + self.activities_budget)

    def _format_config(self, config):
        """Format configuration with instance variables"""
        if isinstance(config, dict):
            return {k: self._format_config(v) for k, v in config.items()}
        elif isinstance(config, str):
            # Calculate derived values
            try:
                # Extract number of days from duration string (e.g., '5 days' -> 5)
                num_days = int(self.duration.split()[0]) if self.duration.split() else 5
            except (ValueError, IndexError):
                num_days = 5  # Default to 5 days if parsing fails
                
            # Calculate per-person and per-day values
            per_person = {
                'transport': self.transport_budget // self.num_people,
                'accommodation': self.accommodation_budget // self.num_people,
                'food': self.food_budget // (self.num_people * num_days),
                'activities': self.activities_budget // self.num_people
            }
            
            # Format all values with commas for better readability
            format_vars = {
                'start_location': self.start_location,
                'destination': self.destination,
                'num_people': self.num_people,
                'budget_range': self.budget_range,
                'budget': f"{self.budget:,}",
                'duration': self.duration,
                'interests': self.interests,
                'transport_budget': f"{self.transport_budget:,}",
                'transport_pp': f"{per_person['transport']:,}",
                'accommodation_budget': f"{self.accommodation_budget:,}",
                'accommodation_pp': f"{per_person['accommodation']:,}",
                'food_budget': f"{self.food_budget:,}",
                'food_pp_pd': f"{per_person['food']:,}",  # Per person per day
                'activities_budget': f"{self.activities_budget:,}",
                'activities_pp': f"{per_person['activities']:,}",
                'misc_budget': f"{self.misc_budget:,}",
                'num_days': num_days
            }
            
            try:
                return config.format(**format_vars)
            except KeyError as e:
                print(f"Warning: Missing key in format string: {e}")
                return config
        return config

    def _create_agents(self, agents_config):
        """Create agent instances from configuration"""
        agents = {}
        for agent_name, config in agents_config.items():
            try:
                agents[agent_name] = Agent(
                    role=config['role'],
                    goal=config['goal'],
                    backstory=config['backstory'],
                    verbose=True,
                    llm=self.llm,
                    tools=[self.search_tool],
                    allow_delegation=True
                )
            except KeyError as e:
                print(f"Error creating agent {agent_name}: Missing required field {e}")
                raise
        return agents
    
    def _create_tasks(self, tasks_config, agents):
        """Create task instances from configuration"""
        tasks = []
        for task_name, config in tasks_config.items():
            try:
                agent_name = config['agent']
                if agent_name not in agents:
                    print(f"Error: Agent '{agent_name}' not found for task '{task_name}'")
                    continue
                    
                task = Task(
                    description=config['description'],
                    agent=agents[agent_name],
                    expected_output=config.get('expected_output')
                )
                tasks.append(task)
            except KeyError as e:
                print(f"Error creating task {task_name}: {e}")
                continue
        return tasks
    
    def _generate_itinerary_header(self):
        """Generate the header section of the itinerary"""
        return f"""# Trip Itinerary: {self.destination}

## Trip Details
- **From**: {self.start_location}
- **To**: {self.destination}
- **Duration**: {self.duration}
- **Travelers**: {self.num_people} {'person' if self.num_people == 1 else 'people'}
- **Budget Range**: {self.budget_range.capitalize()}
- **Total Budget**: ₹{self.budget:,}
- **Interests**: {self.interests}

## Budget Breakdown
- 🚗 Transportation: ₹{self.transport_budget:,} ({self.transport_ratio*100:.0f}%)
- 🏨 Accommodation: ₹{self.accommodation_budget:,} ({self.accommodation_ratio*100:.0f}%)
- 🍽️ Food: ₹{self.food_budget:,} ({self.food_ratio*100:.0f}%)
- 🎭 Activities: ₹{self.activities_budget:,} ({self.activities_ratio*100:.0f}%)
- 💰 Miscellaneous: ₹{self.misc_budget:,} ({self.misc_ratio*100:.0f}%)

## Itinerary
"""
    
    def plan_trip(self):
        """Main method to plan the trip"""
        try:
            # Load YAML configurations
            with open('configs/agents.yaml', 'r') as f:
                agents_config = yaml.safe_load(f) or {}
            with open('configs/tasks.yaml', 'r') as f:
                tasks_config = yaml.safe_load(f) or {}
            
            # Format configurations with instance variables
            agents_config = self._format_config(agents_config)
            tasks_config = self._format_config(tasks_config)
            
            # Create agents and tasks
            agents = self._create_agents(agents_config)
            tasks = self._create_tasks(tasks_config, agents)
            
            if not tasks:
                raise ValueError("No valid tasks were created")
            
            # Create and execute the crew
            trip_crew = Crew(
                agents=list(agents.values()),
                tasks=tasks,
                process=Process.sequential,
                verbose=True,
            )
            
            # Generate markdown output
            result = self._generate_itinerary_header()
            
            # Get itinerary from crew
            print("\n🚀 Starting trip planning process...")
            itinerary = trip_crew.kickoff()
            result += f"\n{itinerary}"
            
            # Add footer with current datetime
            result += f"\n\n---\n*Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}*"
            
            return result
            
        except Exception as e:
            error_msg = f"\n❌ Error planning trip: {str(e)}\n"
            print(error_msg)
            return f"# Trip Planning Error\n\nSorry, we encountered an error while planning your trip:\n\n```\n{error_msg}\n```\n\nPlease check your inputs and try again. If the problem persists, please contact support."