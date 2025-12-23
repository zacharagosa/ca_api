import { LayoutDashboard, BarChart3, PieChart, Activity } from 'lucide-react';

export const DASHBOARDS = [
    {
        id: 'overview',
        title: 'Global Overview',
        url: '/embed/dashboards/4?Session+ID=&Collector+Tstamp+Date=7+day&Player+ID=&Event+Name=&Event+Details=',
        icon: <LayoutDashboard size={20} />
    },
    {
        id: 'battle-royale',
        title: 'Battle Royale Analysis',
        url: '/embed/dashboards/kacsHESOOkjUBInhOaSbUN?Date+Range=14+days&Game+Name=Lookup+Battle+Royale&Game+Version=1.4.4%2C1.4.6%2C1.5.0&Event+1=%22Match_Started%22&Event+2=%22Match_Ended%22&Event+3=%22Skin_Unlocked%22&Event+4=%22in_app_purchase%22&_theme=%7B%22background_color%22%3A%22%230a0e14%22%2C%22base_font_size%22%3A%2214px%22%2C%22color_collection_id%22%3A%22carbon_default%22%2C%22font_family%22%3A%22Inter%22%2C%22text_color%22%3A%22%23e2e8f0%22%7D',
        icon: <BarChart3 size={20} />
    },
    {
        id: 'performance',
        title: 'Revenue & Performance',
        url: '/embed/dashboards/dXqsKbYW2Bo3J4HO1yUUd3?_theme=%7B%22background_color%22%3A%22%230a0e14%22%2C%22base_font_size%22%3A%2214px%22%2C%22color_collection_id%22%3A%22carbon_default%22%2C%22font_family%22%3A%22Inter%22%2C%22text_color%22%3A%22%23e2e8f0%22%7D',
        icon: <PieChart size={20} />
    },
    {
        id: 'gemini-storyteller',
        title: 'Gemini Storyteller',
        url: '/embed/dashboards/GnE3B3qVRlxuTEod5n8Hhm?_theme=%7B%22background_color%22%3A%22%230a0e14%22%2C%22base_font_size%22%3A%2214px%22%2C%22color_collection_id%22%3A%22carbon_default%22%2C%22font_family%22%3A%22Inter%22%2C%22text_color%22%3A%22%23e2e8f0%22%7D',
        icon: <Activity size={20} />
    }
];
