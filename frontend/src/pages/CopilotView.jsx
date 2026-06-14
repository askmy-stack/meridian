import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery } from 'react-query';
import {
  Bot,
  Globe,
  History,
  MapPin,
  Play,
  Send,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import { askCopilot, fetchBacktest } from '../api/client';
import { DemoBanner } from '../components/DemoBanner';
import { ErrorBanner } from '../components/ui/ErrorBanner';
import { LoadingState } from '../components/ui/LoadingState';
import { PageFooterNote, PageHeader } from '../components/ui/PageHeader';
import { Panel } from '../components/ui/Panel';
import { COPILOT_DISCLAIMER, ERRORS, LOADING, NAV_LABELS } from '../lib/uiCopy';

const BACKTEST_IDS = ['suez-2021', 'ukraine-2022'];

const STARTER_PROMPTS = [
  'How is SCRI calculated for our top suppliers?',
  'Why is Taiwan semiconductor risk elevated this week?',
  'Which regions are affected if Red Sea shipping is disrupted?',
  'Walk me through the end-to-end risk pipeline from signals to alerts',
  'Compare Suez canal congestion vs Hormuz closure impact',
  'What SHAP features drive CRITICAL band suppliers?',
];

function parseAnswerSections(answer = '') {
  const sections = [];
  const lines = answer.split('\n').filter(Boolean);
  let current = { title: 'Summary', body: [] };

  for (const line of lines) {
    const heading = line.match(/^#{1,3}\s+(.+)|^([A-Z][^:]+):$/);
    if (heading) {
      if (current.body.length) sections.push({ ...current, body: current.body.join('\n') });
      current = { title: heading[1] || heading[2], body: [] };
    } else {
      current.body.push(line);
    }
  }
  if (current.body.length) sections.push({ ...current, body: current.body.join('\n') });
  return sections.length ? sections : [{ title: 'Answer', body: answer }];
}

function sectionIcon(title) {
  const t = title.toLowerCase();
  if (t.includes('score') || t.includes('scri') || t.includes('risk')) return TrendingUp;
  if (t.includes('region') || t.includes('area') || t.includes('map')) return MapPin;
  if (t.includes('method') || t.includes('how') || t.includes('pipeline')) return Bot;
  if (t.includes('global') || t.includes('country')) return Globe;
  return Sparkles;
}

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

  const answerSections = copilotMutation.data?.answer
    ? parseAnswerSections(copilotMutation.data.answer)
    : [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <DemoBanner />

      <PageHeader
        eyebrow="Phase 6 · Risk copilot"
        title={NAV_LABELS.copilot}
        subtitle="RAG-grounded Q&A — retrieves Qdrant corpus + Neo4j facts. Numeric SCRI always from XGBoost, never from the LLM."
        badges={['RAG · Graph facts']}
        gradient="cyan"
      >
        <p className="text-xs text-amber-200/80 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2 max-w-2xl">
          {COPILOT_DISCLAIMER} Unmatched questions receive an explicit uncertainty response.
        </p>
      </PageHeader>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Panel title="Ask Meridian" subtitle="Covers SCRI methodology, affected regions, and simulator presets">
          <div className="flex gap-2 mb-4">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
              placeholder="e.g. How does SCRI rank our Red Sea exposure?"
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

          <p className="text-xs text-slate-500 mb-2">Suggested prompts</p>
          <div className="flex flex-wrap gap-2 mb-4">
            {STARTER_PROMPTS.map((p) => (
              <button
                key={p}
                type="button"
                className="text-xs px-3 py-1.5 rounded-full border border-slate-700 text-slate-400 hover:border-cyan-500/40 hover:text-cyan-300 text-left"
                onClick={() => handleAsk(p)}
              >
                {p}
              </button>
            ))}
          </div>

          {copilotMutation.isLoading && <LoadingState label={LOADING.copilot} />}

          {copilotMutation.isError && (
            <ErrorBanner
              message={copilotMutation.error?.message || ERRORS.copilot}
              onRetry={() => copilotMutation.mutate(question)}
            />
          )}

          {copilotMutation.data && (
            <div className="space-y-4">
              <div className="flex gap-2 items-center">
                <Bot className="h-5 w-5 text-cyan-400" />
                <span className="text-sm font-medium text-cyan-300">Copilot response</span>
                {copilotMutation.data.grounded === false && (
                  <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border border-amber-500/40 text-amber-300">
                    Low confidence
                  </span>
                )}
              </div>

              {answerSections.map((section) => {
                const Icon = sectionIcon(section.title);
                return (
                  <div
                    key={section.title}
                    className="p-4 rounded-xl border border-slate-700/60 bg-slate-900/40"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <Icon className="h-4 w-4 text-cyan-400" />
                      <h4 className="text-sm font-semibold text-white">{section.title}</h4>
                    </div>
                    <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
                      {section.body}
                    </p>
                  </div>
                );
              })}

              {copilotMutation.data.graph_facts?.length > 0 && (
                <div className="p-4 rounded-xl border border-violet-500/20 bg-violet-500/5">
                  <p className="text-xs font-semibold uppercase tracking-wider text-violet-300 mb-2">
                    Graph facts
                  </p>
                  <ul className="text-sm text-slate-400 space-y-1">
                    {copilotMutation.data.graph_facts.map((fact) => (
                      <li key={fact} className="flex gap-2">
                        <span className="text-violet-400">•</span>
                        {fact}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {copilotMutation.data.citations?.length > 0 && (
                <div className="p-4 rounded-xl border border-slate-700/50">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                    Citations
                  </p>
                  <ul className="space-y-2">
                    {copilotMutation.data.citations.map((c, i) => (
                      <li key={`${c.source}-${i}`} className="text-xs text-slate-500">
                        <span className="text-cyan-400/80 font-mono">
                          [{c.collection?.replace('meridian_', '')}]
                        </span>{' '}
                        {c.text?.slice(0, 160)}
                        {c.text?.length > 160 ? '…' : ''}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {copilotMutation.data.disclaimer && (
                <p className="text-xs text-slate-600">{copilotMutation.data.disclaimer}</p>
              )}

              {copilotMutation.data.suggested_scenario_id && (
                <Link
                  to="/simulate"
                  className="btn-primary inline-flex"
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
              message={ERRORS.backtest}
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

      <PageFooterNote />
    </div>
  );
}
