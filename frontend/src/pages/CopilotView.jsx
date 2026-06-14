import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery } from 'react-query';
import { Bot, History, Play, Send, Sparkles } from 'lucide-react';
import { askCopilot, fetchBacktest } from '../api/client';
import { DemoBanner } from '../components/DemoBanner';
import { ErrorBanner } from '../components/ui/ErrorBanner';
import { LoadingState } from '../components/ui/LoadingState';
import { Panel } from '../components/ui/Panel';

const BACKTEST_IDS = ['suez-2021', 'ukraine-2022'];

const STARTER_PROMPTS = [
  'What happens if Red Sea shipping is disrupted?',
  'Taiwan semiconductor risk for our suppliers',
  'Compare Suez canal congestion impact',
];

export function CopilotView() {
  const [question, setQuestion] = useState('');
  const [activeBacktest, setActiveBacktest] = useState(BACKTEST_IDS[0]);

  const copilotMutation = useMutation((q) => askCopilot(q));

  const backtestQuery = useQuery(
    ['backtest', activeBacktest],
    () => fetchBacktest(activeBacktest),
    { staleTime: 300_000 },
  );

  const handleAsk = (q) => {
    const text = (q ?? question).trim();
    if (text.length < 3) return;
    setQuestion(text);
    copilotMutation.mutate(text);
  };

  return (
    <div className="space-y-6">
      <DemoBanner />
      <header>
        <p className="text-xs font-semibold uppercase tracking-widest text-cyan-400 mb-1">
          Phase 6 · Risk copilot
        </p>
        <h1 className="page-title">Intelligence Copilot</h1>
        <p className="mt-2 text-slate-400 max-w-2xl">
          RAG-grounded responses — retrieves Qdrant corpus + Neo4j facts. Numeric SCRI never from LLM.
        </p>
        <p className="mt-3 text-xs text-amber-200/80 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2 max-w-2xl">
          Disclaimer: Answers cite retrieved documents and graph facts. Risk scores come from XGBoost only.
          Unmatched questions receive an explicit uncertainty response.
        </p>
      </header>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Panel title="Ask Meridian" subtitle="Maps keywords → simulator presets + graph context">
          <div className="flex gap-2 mb-4">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
              placeholder="e.g. Red Sea Houthi attacks on our lanes…"
              className="flex-1 px-4 py-3 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder:text-slate-600 focus:border-cyan-500/50 outline-none"
              aria-label="Copilot question"
            />
            <button
              type="button"
              className="btn-primary shrink-0"
              disabled={copilotMutation.isLoading}
              onClick={() => handleAsk()}
            >
              <Send className="h-4 w-4" />
              Ask
            </button>
          </div>

          <div className="flex flex-wrap gap-2 mb-4">
            {STARTER_PROMPTS.map((p) => (
              <button
                key={p}
                type="button"
                className="text-xs px-3 py-1.5 rounded-full border border-slate-700 text-slate-400 hover:border-cyan-500/40 hover:text-cyan-300"
                onClick={() => handleAsk(p)}
              >
                {p}
              </button>
            ))}
          </div>

          {copilotMutation.isLoading && <LoadingState label="Analyzing graph context…" />}

          {copilotMutation.isError && (
            <ErrorBanner
              message={
                copilotMutation.error?.message ||
                'Copilot request failed — check API, Qdrant, and Neo4j are running.'
              }
              onRetry={() => copilotMutation.mutate(question)}
            />
          )}

          {copilotMutation.data && (
            <div className="p-4 rounded-xl border border-cyan-500/30 bg-cyan-500/5">
              <div className="flex gap-2 mb-2">
                <Bot className="h-5 w-5 text-cyan-400" />
                <span className="text-sm font-medium text-cyan-300">Copilot</span>
              </div>
              <p className="text-sm text-slate-200 leading-relaxed">{copilotMutation.data.answer}</p>
              {copilotMutation.data.disclaimer && (
                <p className="text-xs text-slate-500 mt-2">{copilotMutation.data.disclaimer}</p>
              )}
              {copilotMutation.data.citations?.length > 0 && (
                <div className="mt-3 pt-3 border-t border-slate-700/50">
                  <p className="text-xs font-medium text-slate-400 mb-2">Citations</p>
                  <ul className="space-y-1.5">
                    {copilotMutation.data.citations.map((c, i) => (
                      <li key={`${c.source}-${i}`} className="text-xs text-slate-500">
                        <span className="text-cyan-400/80">[{c.collection?.replace('meridian_', '')}]</span>{' '}
                        {c.text?.slice(0, 120)}
                        {c.text?.length > 120 ? '…' : ''}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {copilotMutation.data.grounded === false && (
                <p className="text-xs text-amber-400/80 mt-2">Low confidence — limited grounding context</p>
              )}
              {copilotMutation.data.graph_facts?.length > 0 && (
                <p className="text-xs text-slate-500 mt-1">
                  Graph facts: {copilotMutation.data.graph_facts.join(' · ')}
                </p>
              )}
              {copilotMutation.data.suggested_scenario_id && (
                <Link
                  to="/simulate"
                  className="btn-primary mt-4 inline-flex"
                  state={{ scenarioId: copilotMutation.data.suggested_scenario_id }}
                >
                  <Play className="h-4 w-4" />
                  Run {copilotMutation.data.suggested_scenario_id.replace(/-/g, ' ')}
                </Link>
              )}
            </div>
          )}
        </Panel>

        <Panel title="Historical backtest" subtitle="Replay past disruptions on today's supplier graph">
          <div className="flex gap-2 mb-4">
            {BACKTEST_IDS.map((id) => (
              <button
                key={id}
                type="button"
                onClick={() => setActiveBacktest(id)}
                className={`px-3 py-2 text-sm rounded-xl border capitalize ${
                  activeBacktest === id
                    ? 'bg-violet-500/20 border-violet-500/40 text-violet-300'
                    : 'border-slate-700 text-slate-400'
                }`}
              >
                {id.replace('-', ' ')}
              </button>
            ))}
          </div>

          {backtestQuery.isLoading && <LoadingState />}

          {backtestQuery.isError && (
            <ErrorBanner
              message="Could not load backtest data — run `make backtest-scri` and ensure the API is up."
              onRetry={() => backtestQuery.refetch()}
            />
          )}

          {backtestQuery.data && (
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <History className="h-5 w-5 text-violet-400 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-white">{backtestQuery.data.backtest?.title}</h3>
                  <p className="text-sm text-slate-400 mt-1">{backtestQuery.data.backtest?.description}</p>
                </div>
              </div>
              <p className="text-sm">
                <span className="text-slate-500">Would affect today: </span>
                <span className="text-amber-400 font-semibold">
                  {backtestQuery.data.would_affect_today} suppliers
                </span>
              </p>
              <ul className="text-sm text-slate-400 space-y-1">
                {backtestQuery.data.backtest?.lessons?.map((lesson) => (
                  <li key={lesson} className="flex gap-2">
                    <Sparkles className="h-3.5 w-3.5 text-violet-400 shrink-0 mt-0.5" />
                    {lesson}
                  </li>
                ))}
              </ul>
              <Link to="/map" className="btn-ghost">
                View region on map
              </Link>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
