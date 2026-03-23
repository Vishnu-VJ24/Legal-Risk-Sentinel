import { Cell, Pie, PieChart, ResponsiveContainer } from 'recharts';
import type { AnalysisResult } from '../../types/contracts';
import { AnimatedNumber } from './AnimatedNumber';

interface RiskOverviewPanelProps {
  results: AnalysisResult;
}

const colors = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#22c55e',
};

export const RiskOverviewPanel = ({ results }: RiskOverviewPanelProps) => {
  const chartData = Object.entries(results.risk_distribution).map(([name, value]) => ({ name, value }));

  return (
    <section className="grid gap-6 rounded-[28px] border border-border bg-surface/85 p-6 xl:grid-cols-[1fr_1.4fr]">
      <div className="h-[260px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie innerRadius={72} outerRadius={110} data={chartData} dataKey="value" nameKey="name" paddingAngle={5}>
              {chartData.map((entry) => (
                <Cell key={entry.name} fill={colors[entry.name as keyof typeof colors]} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-border p-5">
          <p className="text-sm text-text-secondary">Overall Risk Score</p>
          <p className="mt-2 text-5xl font-bold text-primary">
            <AnimatedNumber value={results.overall_risk_score} />
          </p>
        </div>
        <div className="rounded-2xl border border-border p-5">
          <p className="text-sm text-text-secondary">Review Time Estimate</p>
          <p className="mt-2 text-3xl font-semibold">{Math.ceil(results.total_clauses * 2.2)} min</p>
        </div>
        <div className="rounded-2xl border border-border p-5">
          <p className="text-sm text-text-secondary">Total Clauses Found</p>
          <p className="mt-2 text-3xl font-semibold">{results.total_clauses}</p>
        </div>
        <div className="rounded-2xl border border-border p-5">
          <p className="text-sm text-text-secondary">High Risk Count</p>
          <p className="mt-2 text-3xl font-semibold">
            {results.risk_distribution.critical + results.risk_distribution.high}
          </p>
        </div>
      </div>
    </section>
  );
};
