import { LayoutDashboard, BarChart3, PieChart, Activity } from 'lucide-react';

const ICON_MAP = {
    'LayoutDashboard': LayoutDashboard,
    'BarChart3': BarChart3,
    'PieChart': PieChart,
    'Activity': Activity
};

const DEFAULT_DASHBOARDS = [
    {
        id: 'overview',
        title: 'How Many times did a player do X?',
        url: '/embed/dashboards/4?Session+ID=&Collector+Tstamp+Date=7+day&Player+ID=&Event+Name=&Event+Details=',
        icon: 'LayoutDashboard'
    },
    {
        id: 'battle-royale',
        title: 'Session Explorer',
        url: '/embed/dashboards/5?Session+ID=C58FCAC8-422C-FD77-5AEE-BE989C4E7C00',
        icon: 'BarChart3'
    },
    {
        id: 'performance',
        title: 'Player Explorer',
        url: '/embed/dashboards/3?Session+ID=&Player+ID=A6025281-4A9B-AB5A-A7AD-0B8901FAAA1E&Session+Start+Date=7+day',
        icon: 'PieChart'
    },
    {
        id: 'gemini-storyteller',
        title: 'Weapon Stats Dashboard',
        url: '/embed/dashboards/1?Collector+Tstamp+Date=2+days&Weapon+Equipped+Count=%3E5&Map+Name=',
        icon: 'Activity'
    }
];

const getDashboards = () => {
    try {
        const envConfig = import.meta.env.VITE_DASHBOARDS_CONFIG;
        if (envConfig) {
            const parsed = JSON.parse(envConfig);
            return parsed.map(dashboard => ({
                ...dashboard,
                icon: ICON_MAP[dashboard.icon] ?
                    (() => { const Icon = ICON_MAP[dashboard.icon]; return <Icon size={20} /> })() :
                    <LayoutDashboard size={20} />
            }));
        }
    } catch (e) {
        console.warn('Failed to parse VITE_DASHBOARDS_CONFIG, using default dashboards', e);
    }

    return DEFAULT_DASHBOARDS.map(dashboard => ({
        ...dashboard,
        icon: ICON_MAP[dashboard.icon] ?
            (() => { const Icon = ICON_MAP[dashboard.icon]; return <Icon size={20} /> })() :
            <LayoutDashboard size={20} />
    }));
};

export const DASHBOARDS = getDashboards();
