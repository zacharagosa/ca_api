// OLD QUESTIONS (Commented out for reference)
/*
export const STARTER_QUESTIONS = [
    "Count the total number of events for the last 7 days broken down by event name.",
    "Show me the daily count of unique users (events.user_count) for the last week.",
];

export const DEEP_TEST_QUESTIONS = [
    { label: "Frequency Analysis", question: "How many times was the 'OnWeaponFired' event triggered in the last 24 hours? Group by the weapon type used." },
    { label: "Engagement Trends", question: "Analyze the daily trend of 'OnWeaponFired' vs 'OnDeath' events for the last 30 days." },
    { label: "Platform Analysis", question: "Compare the total event count and distinct user count (events.user_count) for 'active' vs 'inactive' player contexts for the last month." },
    { label: "OS Distribution", question: "Break down the total number of events by 'os_name' for the last 7 days. Which top 3 operating systems are generating the most activity?" },
    { label: "App ID Performance", question: "Calculate the total event count for each 'app_id' over the last 30 days. Which app is driving the most engagement?" },
    { label: "Error Tracking", question: "Identify any events with names containing 'error' or 'fail' in the last 24 hours." },
    { label: "User Retention", question: "Compare the number of returning sessions vs new sessions for the last week." },
    { label: "Time of Day Analysis", question: "Group the total event count by the hour of the day for the last month. When are users most active?" },
    { label: "Browser Performance", question: "Compare the total event count for users on 'Chrome' vs 'Safari'. Is there a discrepancy in engagement volume across browsers?" }
];
*/

// NEW QUESTIONS (Based on actual 'gaming/events' model metadata)
export const STARTER_QUESTIONS = [
    "User Overview: How many active users did we have in the last 7 days?",
    "Revenue Check: What is the total revenue broken down by country for the last 30 days?",
    "Retention Rate: What is the Day 1 Retention Rate for the past month?"
];

export const DEEP_TEST_QUESTIONS = [
    {
        label: "Monetization Analysis",
        question: "Compare ARPU vs ARPPU. Show me the daily trend of Average Revenue Per User and Average Revenue Per Spender for the last 30 days."
    },
    {
        label: "Geographic Performance",
        question: "Which countries are most valuable? Breakdown Total Revenue, Number of Users, and Average Revenue Per User by Country for the current month, ordered by Revenue descending."
    },
    {
        label: "Platform Engagement",
        question: "Analyze engagement by Platform. Compare Average Session Length and Number of Sessions grouped by Platform for the last 14 days."
    },
    {
        label: "User Acquisition ROI",
        question: "Evaluate our marketing spend. Calculate Return on Ad Spend (ROAS) and Cost Per Install (CPI) by Traffic Source for the last quarter."
    },
    {
        label: "Retention Funnel",
        question: "How well do we retain users? Show me a retention curve plotting Day 1, Day 7, Day 14, and Day 30 Retention Rates for users acquired in the last 90 days."
    }
];
