
import { useState } from 'react';
import { Loader2, ExternalLink } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const LookerLink = ({ url, onLinkClick, className, iconSize = 14 }) => {
    const [isLoading, setIsLoading] = useState(false);

    const handleClick = async (e) => {
        e.preventDefault();
        if (onLinkClick) {
            onLinkClick(url);
            return;
        }

        // Fallback internal signing if no handler provided
        setIsLoading(true);
        try {
            const response = await fetch(`${API_BASE_URL}/api/embed`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_url: url })
            });

            if (!response.ok) throw new Error('Signing failed');

            const data = await response.json();
            window.open(data.url, '_blank');
        } catch (err) {
            console.error("Failed to open Looker link:", err);
            window.open(url, '_blank');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <a
            href={url}
            onClick={handleClick}
            className={`action-link cursor-pointer flex items-center gap-1 ${isLoading ? 'opacity-70' : 'opacity-100'} ${className || ''}`}
        >
            {isLoading ? <Loader2 size={iconSize} className="animate-spin" /> : <ExternalLink size={iconSize} />}
            <span>{isLoading ? 'Opening...' : 'View Source Query'}</span>
        </a>
    );
};
