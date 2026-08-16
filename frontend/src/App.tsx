import React, { useState } from 'react';
import { Sparkles, Activity, Info, AlertCircle } from 'lucide-react';
import { scoreTitle } from './services/api';
import type { ScoreResponse } from './services/api';

const EXAMPLES = [
  "I Bought a $700 Driver! Worth It or Wasted?",
  "Live Crypto Trading | Bitcoin | ETHUSD Live Analysis",
  "Reacting to my Youtube comments #funny #reaction",
  "Fire Emblem Fortunes Weave Nintendo Direct Announced",
  "ASMR Gaming Fortnite Looking for New Sprites Relaxing"
];

function getLabelFromPercentile(p: number) {
  if (p >= 90) return { text: "Viral Potential", color: "text-accent" };
  if (p >= 75) return { text: "Well Above Average", color: "text-success" };
  if (p >= 50) return { text: "Above Average", color: "text-primary" };
  if (p >= 25) return { text: "Below Average", color: "text-textSecondary" };
  return { text: "Low Engagement", color: "text-danger" };
}

function App() {
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(false);
  const [isWaking, setIsWaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ScoreResponse | null>(null);

  const charCount = title.length;
  const isNearMax = charCount > 180;
  const isMax = charCount >= 200;

  const handleSubmit = async (e?: React.FormEvent, overrideTitle?: string) => {
    if (e) e.preventDefault();
    const targetTitle = overrideTitle ?? title;

    if (!targetTitle.trim() || targetTitle.length > 200) return;

    setLoading(true);
    setIsWaking(false);
    setError(null);
    
    // Cloud instances (Render free tier) spin down and take time to wake up
    const wakingTimer = setTimeout(() => {
      setIsWaking(true);
    }, 4000);

    try {
      const res = await scoreTitle(targetTitle);
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'An error occurred while scoring.');
    } finally {
      clearTimeout(wakingTimer);
      setLoading(false);
      setIsWaking(false);
    }
  };

  return (
    <div className="min-h-screen bg-background relative overflow-hidden flex flex-col items-center py-12 px-4 sm:px-6 lg:px-8">

      <main className="w-full max-w-5xl z-10 flex flex-col gap-10">
        
        {/* Header */}
        <header className="text-center space-y-4 mb-2">
          <div className="inline-flex items-center justify-center p-3 bg-surface border border-white/10 rounded-2xl mb-2 shadow-lg">
            <Activity className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-primary to-accent pb-2">
            TitlePulse
          </h1>
          <p className="text-lg text-textSecondary max-w-2xl mx-auto">
            Predict the true virality of your YouTube title, normalized for channel size.
          </p>
        </header>

        {/* Two Column Layout Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 w-full items-stretch">
          
          {/* Main Panel (Left Column) */}
          <section className="glass-panel p-6 md:p-8 flex flex-col gap-6">
            <form onSubmit={handleSubmit} className="relative group flex flex-col gap-2">
              <div className="relative flex items-center">
                <input
                  type="text"
                  className="glass-input pr-32 text-lg font-medium"
                  placeholder="Paste your YouTube title here..."
                  value={title}
                  onChange={e => setTitle(e.target.value)}
                  maxLength={200}
                />
                <button
                  type="submit"
                  disabled={!title.trim() || loading || isMax}
                  className="absolute right-2 top-1/2 -translate-y-1/2 glass-button !px-4 !py-2 flex items-center gap-2"
                >
                  {loading ? <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <><Sparkles className="w-4 h-4" /> Score</>}
                </button>
              </div>

              {/* Character Counter & Error Inline */}
              <div className="flex justify-between items-center px-1">
                <div className="text-sm">
                  {error ? (
                    <span className="text-danger flex items-center gap-1"><AlertCircle className="w-4 h-4" /> {error}</span>
                  ) : (
                    <span className="text-textSecondary/50">Press Enter to score</span>
                  )}
                </div>
                <div className={`text-xs font-mono transition-colors ${isMax ? 'text-danger' : isNearMax ? 'text-accent' : 'text-textSecondary/50'}`}>
                  {charCount} / 200
                </div>
              </div>
            
              {/* Waking Up Indicator */}
              {isWaking && (
                <div className="mt-2 text-sm text-accent flex items-center justify-center gap-2 animate-pulse bg-accent/10 py-2 rounded-lg border border-accent/20">
                  <Activity className="w-4 h-4" />
                  <span>Waking up the server — first request may take a moment...</span>
                </div>
              )}
            </form>

            {/* Example Chips */}
            <div className="flex flex-col gap-3 mt-auto">
              <span className="text-xs font-semibold text-textSecondary uppercase tracking-wider">Try an example</span>
              <div className="flex flex-wrap gap-2">
                {EXAMPLES.map((ex, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => {
                      setTitle(ex);
                      handleSubmit(undefined, ex);
                    }}
                    className="chip text-left"
                  >
                    {ex}
                  </button>
                ))}
              </div>
            </div>
          </section>

          {/* Results Panel (Right Column) */}
          {result ? (
            <section className="glass-panel p-6 md:p-8 animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col justify-center">
              <div className="flex flex-col gap-8">
                
                <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
                  <div className="flex flex-col gap-1">
                    <h2 className="text-sm font-semibold text-textSecondary uppercase tracking-wider">Engagement Score</h2>
                    <div className="flex items-baseline gap-3">
                      <span className="text-5xl font-black text-textPrimary tracking-tighter">
                        {result.engagement_score.toFixed(3)}
                      </span>
                      <span className={`text-xl font-medium ${getLabelFromPercentile(result.percentile).color}`}>
                        {getLabelFromPercentile(result.percentile).text}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Percentile Bar */}
                <div className="flex flex-col gap-2">
                  <div className="flex justify-between text-sm text-textSecondary font-medium">
                    <span>0th Percentile</span>
                    <span>{result.percentile.toFixed(1)}th Percentile</span>
                    <span>100th</span>
                  </div>
                  <div className="h-4 w-full bg-surface rounded-full overflow-hidden border border-white/5">
                    <div
                      className="h-full bg-gradient-to-r from-primary to-accent transition-all duration-1000 ease-out relative"
                      style={{ width: `${result.percentile}%` }}
                    >
                      <div className="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-white/20 to-transparent" />
                    </div>
                  </div>
                </div>

                <div className="bg-surface/50 rounded-xl p-4 border border-white/5 flex items-start gap-3 mt-auto">
                  <Info className="w-5 h-5 text-primary shrink-0 mt-0.5" />
                  <p className="text-sm text-textSecondary leading-relaxed">
                    <strong className="text-textPrimary">What this means:</strong> This score isolates the title's effect by normalizing against the channel's typical views.
                    It only reflects the title text—it does not account for thumbnail quality, video timing, or current trends.
                  </p>
                </div>

              </div>
            </section>
          ) : (
            <section className="glass-panel p-6 md:p-8 flex flex-col items-center justify-center min-h-[300px] border-dashed border-2 border-white/10 bg-surface/30">
              {loading ? (
                 <div className="flex flex-col items-center gap-4">
                   <div className="w-10 h-10 border-4 border-white/10 border-t-primary rounded-full animate-spin" />
                   {isWaking && <p className="text-sm text-textSecondary animate-pulse">Waking up server...</p>}
                 </div>
              ) : (
                <>
                  <Sparkles className="w-8 h-8 text-textSecondary/30 mb-4" />
                  <p className="text-textSecondary font-medium">Enter a title to see its score</p>
                </>
              )}
            </section>
          )}
        </div>

        {/* How it works */}
        <section className="w-full mt-4 mb-4 flex flex-col gap-8">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-textPrimary">How it works</h2>
            <p className="text-textSecondary mt-2 max-w-2xl mx-auto">
              TitlePulse predicts engagement by isolating the title's effect from the channel's inherent size.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="glass-panel p-6 flex flex-col gap-3 border border-white/5">
              <div className="flex items-center gap-3 mb-1">
                <div className="w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center font-bold text-sm">1</div>
                <h3 className="font-bold text-textPrimary">Data Collection</h3>
              </div>
              <p className="text-sm text-textSecondary leading-relaxed">Video metadata is pulled via the YouTube API.</p>
            </div>
            <div className="glass-panel p-6 flex flex-col gap-3 border border-white/5">
              <div className="flex items-center gap-3 mb-1">
                <div className="w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center font-bold text-sm">2</div>
                <h3 className="font-bold text-textPrimary">Normalization</h3>
              </div>
              <p className="text-sm text-textSecondary leading-relaxed">Views are normalized against the channel's own average to isolate the title's impact.</p>
            </div>
            <div className="glass-panel p-6 flex flex-col gap-3 border border-white/5">
              <div className="flex items-center gap-3 mb-1">
                <div className="w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center font-bold text-sm">3</div>
                <h3 className="font-bold text-textPrimary">Prediction</h3>
              </div>
              <p className="text-sm text-textSecondary leading-relaxed">A TF-IDF Ridge Model predicts the engagement score, achieving a <strong className="text-primary font-bold">0.246 Spearman correlation</strong>.</p>
            </div>
          </div>
        </section>

        {/* Footer info */}
        <footer className="mt-8 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-textSecondary">
          <div className="flex items-center gap-2 bg-surface/50 px-4 py-2 rounded-full border border-white/5">
            <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
            Powered by TF-IDF Ridge Model (0.246 Spearman)
          </div>
          <a href="https://github.com/Samyak40/Youtube_Title_Rater" target="_blank" rel="noreferrer" className="flex items-center gap-2 hover:text-primary transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.02c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A4.8 4.8 0 0 0 8 18v4" /><line x1="9" x2="9.01" y1="9" y2="9" /></svg>
            View Repository
          </a>
        </footer>

      </main>
    </div>
  );
}

export default App;
