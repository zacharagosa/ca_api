import { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ChevronUp, ChevronDown } from 'lucide-react';
import { LookerLink } from '@/components/LookerLink';

const DataTableRenderer = ({ data, link, onLinkClick }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    if (!data || !data.rows || data.rows.length === 0) return null;

    const PREVIEW_ROWS = 3;
    const showExpandControl = data.rows.length > PREVIEW_ROWS;
    // If expanded, show all. If not, show preview.
    const displayRows = isExpanded ? data.rows : data.rows.slice(0, PREVIEW_ROWS);

    return (
        <div className="mt-4 w-full rounded-md border bg-background text-foreground overflow-hidden">
            {/* Header / Summary Line */}
            <div className="bg-muted/50 p-3 flex items-center justify-between gap-2 border-b">
                <div className="flex items-center gap-3">
                    <span className="font-semibold text-sm text-muted-foreground">Data Table ({data.rows.length} rows)</span>

                    {/* Integrated Source Link */}
                    {link && (
                        <div className="flex items-center gap-1 pl-3 border-l border-muted-foreground/20">
                            <LookerLink
                                url={link}
                                onLinkClick={onLinkClick}
                                iconSize={12}
                                className="text-xs h-auto p-0 text-blue-500 hover:text-blue-600 font-medium no-underline hover:underline"
                            />
                        </div>
                    )}
                </div>

                {showExpandControl && (
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setIsExpanded(!isExpanded)}
                        className="h-6 text-xs gap-1 hover:bg-background/50 px-2"
                    >
                        {isExpanded ? (
                            <>Show Less <ChevronUp size={12} /></>
                        ) : (
                            <>Expand <ChevronDown size={12} /></>
                        )}
                    </Button>
                )}
            </div>

            <div className="p-0 overflow-x-auto">
                <Table>
                    <TableHeader>
                        <TableRow>
                            {data.fields.map((f, i) => (
                                <TableHead key={i} className="h-8 text-xs px-4 bg-muted/20">{f.label}</TableHead>
                            ))}
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {displayRows.map((row, i) => (
                            <TableRow key={i} className="hover:bg-muted/50">
                                {data.fields.map((f, j) => (
                                    <TableCell key={j} className="py-2 text-xs px-4">
                                        {f.name.includes('percent') || f.name.includes('rate') ?
                                            `${(Number(row[f.name]) * 100).toFixed(2)}%` :
                                            (typeof row[f.name] === 'number' && !Number.isInteger(row[f.name])) ?
                                                Number(row[f.name]).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) :
                                                row[f.name]
                                        }
                                    </TableCell>
                                ))}
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </div>

            {showExpandControl && !isExpanded && (
                <div className="bg-muted/20 p-1 text-center border-t">
                    <button
                        onClick={() => setIsExpanded(true)}
                        className="text-[10px] text-muted-foreground hover:text-foreground uppercase tracking-wider font-semibold w-full py-1"
                    >
                        Show {data.rows.length - PREVIEW_ROWS} More Rows
                    </button>
                </div>
            )}
        </div>
    );
};

export default DataTableRenderer;
