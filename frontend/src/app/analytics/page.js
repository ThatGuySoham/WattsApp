"use client"
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { formatNum, formatKwh } from "@/lib/format";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip } from 'recharts';
import { Brain, Activity, Target, Zap } from "lucide-react";
import { toast } from "sonner";

export default function AnalyticsPage() {
  const [household, setHousehold] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      setLoading(true);
      const hhs = await api.households();
      if (hhs.length > 0) {
        setHousehold(hhs[0]);
        const rep = await api.modelReport(hhs[0].id);
        setReport(rep);
      }
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <div className="space-y-6"><Skeleton className="h-10 w-48" /><Skeleton className="h-64 w-full" /></div>;
  if (!report) return <div>No model data found.</div>;

  const { model, diagnostics: diag } = report;

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
          <Brain className="size-8 text-teal" /> AI Analytics & Predictions
        </h1>
        <p className="text-muted-foreground mt-1">Linear Regression Model Diagnostics</p>
      </div>

      <div className="grid md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm font-medium text-muted-foreground mb-1 flex items-center gap-2">
              <Target className="size-4" /> Model Accuracy (R²)
            </div>
            <div className="text-2xl font-bold">{formatNum(model.r_squared, 3)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm font-medium text-muted-foreground mb-1 flex items-center gap-2">
              <Activity className="size-4" /> Mean Abs Error
            </div>
            <div className="text-2xl font-bold">{formatNum(diag.mae_wh)} Wh</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm font-medium text-muted-foreground mb-1 flex items-center gap-2">
              <Zap className="size-4" /> Top Driver
            </div>
            <div className="text-2xl font-bold capitalize">{diag.top_driver.replace(/_/g, ' ')}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm font-medium text-muted-foreground mb-1">Samples Trained</div>
            <div className="text-2xl font-bold">{formatNum(diag.n_samples, 0)}</div>
          </CardContent>
        </Card>
      </div>

      <Card className="bg-white">
        <CardHeader>
          <CardTitle>The Math: Multiple Linear Regression</CardTitle>
          <CardDescription>
            The system predicts daily energy consumption (Wh) for each appliance based on these learned weights.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="bg-secondary p-4 rounded-xl font-mono text-sm overflow-x-auto whitespace-nowrap">
            <span className="text-primary font-bold">Predicted Wh</span> = 
            {' '}<span className="text-teal">{formatNum(model.intercept)}</span> (Base)
            <br/>&nbsp;&nbsp;+ <span className="text-teal">{formatNum(model.coefficient_hours)}</span> × Hours Used
            <br/>&nbsp;&nbsp;+ <span className="text-teal">{formatNum(model.coefficient_watts)}</span> × Power Rating (Watts)
            <br/>&nbsp;&nbsp;+ <span className="text-teal">{formatNum(model.coefficient_age)}</span> × Age (Years)
          </div>
          
          <div className="mt-8">
            <h3 className="font-semibold mb-4 text-foreground">Standardized Factor Importance</h3>
            <div className="space-y-4">
              {diag.factors.map(f => (
                <div key={f.feature}>
                  <div className="flex justify-between text-sm mb-1">
                    <span>{f.label}</span>
                    <span className="font-medium">{formatNum(f.share * 100)}%</span>
                  </div>
                  <div className="h-2 bg-secondary rounded-full overflow-hidden">
                    <div className="h-full bg-teal rounded-full" style={{ width: `${f.share * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="bg-white">
        <CardHeader>
          <CardTitle>Actual vs Predicted Consumption</CardTitle>
          <CardDescription>Visualizing model accuracy across a sample of {diag.points.length} daily usage logs.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[400px] w-full mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" />
                <XAxis type="number" dataKey="actual_wh" name="Actual Wh" tick={{fill: '#78716c'}} />
                <YAxis type="number" dataKey="predicted_wh" name="Predicted Wh" tick={{fill: '#78716c'}} />
                <RechartsTooltip cursor={{ strokeDasharray: '3 3' }} 
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-popover text-popover-foreground border shadow-md p-3 rounded-lg text-sm">
                          <p className="font-bold mb-1">{data.appliance_name}</p>
                          <p>Actual: {formatNum(data.actual_wh)} Wh</p>
                          <p>Predicted: {formatNum(data.predicted_wh)} Wh</p>
                          <p className="text-muted-foreground mt-1">{data.hours_used} hours</p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Scatter name="Logs" data={diag.points} fill="var(--coral)" fillOpacity={0.6} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
