
from trip_planner import TripPlanner
import os
from datetime import datetime

def get_budget_range():
    while True:
        print("\nSelect budget range:")
        print("1. Low (Budget Travel)")
        print("2. Mid (Standard Travel)")
        print("3. High (Luxury Travel)")
        choice = input("Enter your choice (1-3): ")
        if choice in ['1', '2', '3']:
            return ['low', 'mid', 'high'][int(choice) - 1]
        print("Invalid choice. Please select 1, 2, or 3.")

if __name__ == "__main__":
    # Get user input for trip details
    print("\n=== Trip Planner ===\n")
    start_location = input("Enter your starting city: ").strip()
    destination = input("Enter your destination: ").strip()
    num_people = int(input("Enter number of people traveling: ").strip() or "1")
    budget_range = get_budget_range()
    budget = input(f"Enter your total budget in INR (e.g., 50000): ").strip()
    duration = input("Enter trip duration (e.g., '7 days' or '2 weeks'): ").strip()
    interests = input("Enter your interests (e.g., adventure, culture, food, nature): ").strip()

    # Create a TripPlanner instance with all parameters
    trip_planner = TripPlanner(
        start_location=start_location,
        destination=destination,
        num_people=num_people,
        budget_range=budget_range,
        budget=budget,
        duration=duration,
        interests=interests
    )

    # Plan the trip
    print("\nPlanning your trip...")
    result = trip_planner.plan_trip()
    
    os.makedirs("trip_plans", exist_ok=True)
    # Save to markdown file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"trip_plans/{destination.lower().replace(' ', '_')}_{timestamp}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(result)
    
    print(f"\n✅ Trip plan saved to {os.path.abspath(filename)}")
