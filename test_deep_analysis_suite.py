import os
import time
from agent import run_deep_analysis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define Test Scenarios
SCENARIOS = [
    {
        "name": "Scenario 1: UA Performance Analysis",
        "question": "Analyze the ROAS (Return on Ad Spend) by Campaign for the last 30 days. Which campaigns are performing best and should be scaled?"
    },
    {
        "name": "Scenario 2: Player Behavior Comparison",
        "question": "Compare the average session length and retention rates (D1, D7) of paying users vs non-paying users for the game 'Looker Battle Royale' over the last 3 months."
    },
    {
        "name": "Scenario 3: Market Trend Analysis",
        "question": "What are the top 3 countries by revenue for the last quarter? For these countries, how does the ARPU compare?"
    }
]

def run_test_suite():
    print("="*60)
    print("🚀 STARTING DEEP ANALYSIS AUTO-TEST SUITE")
    print("="*60)
    
    results_dir = "test_results"
    os.makedirs(results_dir, exist_ok=True)
    
    for i, scenario in enumerate(SCENARIOS):
        print(f"\n\n🔹 Running {scenario['name']}...")
        print(f"❓ Question: {scenario['question']}")
        print("-" * 40)
        
        start_time = time.time()
        output_text = []
        
        try:
            # Run the generator
            for chunk in run_deep_analysis(scenario['question']):
                content = chunk.get('content', {})
                parts = content.get('parts', [])
                for part in parts:
                    text = part.get('text', '')
                    if text:
                        print(text, end="", flush=True)
                        output_text.append(text)
            
            duration = time.time() - start_time
            print(f"\n\n✅ Completed in {duration:.2f} seconds.")
            
            # Save Report
            filename = f"{results_dir}/scenario_{i+1}_report.md"
            with open(filename, "w") as f:
                f.write(f"# {scenario['name']}\n\n")
                f.write(f"**Question:** {scenario['question']}\n\n")
                f.write(f"**Duration:** {duration:.2f}s\n\n")
                f.write("## Agent Output\n\n")
                f.write("".join(output_text))
            
            print(f"📄 Report saved to {filename}")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")

    print("\n" + "="*60)
    print("🏁 TEST SUITE FINISHED")
    print("="*60)

if __name__ == "__main__":
    run_test_suite()
