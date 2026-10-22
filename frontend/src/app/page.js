"use client"
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { formatINR, formatKwh, formatNum } from "@/lib/format";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Zap, IndianRupee, Clock, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

export default function Dashboard() {
  const [household, setHousehold] = useState(null);
  const [appliances, setAppliances] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(true);

  // New appliance state
  const [newName, setNewName] = useState("");
  const [newCat, setNewCat] = useState("Kitchen");
  const [newWatts, setNewWatts] = useState("");
  const [newAge, setNewAge] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      setLoading(true);
      const hhs = await api.households();
      if (hhs.length > 0) {
        const hh = hhs[0];
        setHousehold(hh);
        const apps = await api.appliances(hh.id);
        setAppliances(apps);
        
        // Load prediction/bill
        const pred = await api.predict({
          household_id: hh.id,
          days: hh.state === "Tamil Nadu" ? 60 : 30
        });
        setPrediction(pred);
      }
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleAddAppliance(e) {
    e.preventDefault();
    if (!household) return;
    try {
      await api.createAppliance(household.id, {
        appliance_name: newName,
        category: newCat,
        power_rating_watts: parseInt(newWatts),
        age_years: parseInt(newAge),
        is_smart: false
      });
      toast.success("Appliance added");
      setNewName(""); setNewWatts(""); setNewAge("");
      loadData();
    } catch(err) {
      toast.error(err.message);
    }
  }

  async function handleDelete(id) {
    try {
      await api.deleteAppliance(id);
      toast.success("Appliance deleted");
      loadData();
    } catch(err) {
      toast.error(err.message);
    }
  }

  if (loading) {
    return <div className="space-y-6"><Skeleton className="h-10 w-48" /><Skeleton className="h-64 w-full" /></div>;
  }
  if (!household) return <div>No household data found. Run backend seeder.</div>;

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">{household.name}</h1>
          <p className="text-muted-foreground mt-1">{household.state} • Operational Dashboard</p>
        </div>
      </div>

      {prediction && (
        <div className="grid md:grid-cols-3 gap-6">
          <Card className="bg-gradient-to-br from-primary/10 to-primary/5 border-primary/20">
            <CardHeader className="pb-2">
              <CardDescription className="font-medium text-primary">Estimated Bill ({prediction.forecast.days} days)</CardDescription>
              <CardTitle className="text-4xl text-primary">{formatINR(prediction.bill.total_inr)}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm text-muted-foreground flex justify-between mt-2">
                <span>Total Units: {formatKwh(prediction.forecast.total_kwh)}</span>
                <span className="font-medium text-foreground">{prediction.bill.discom}</span>
              </div>
            </CardContent>
          </Card>

          <Card className="md:col-span-2">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2">
                <Zap className="size-5 text-sun" /> Top Energy Guzzlers
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4 mt-2">
                {prediction.guzzlers.map((g, i) => (
                  <div key={g.appliance_id} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="size-8 rounded-full bg-secondary flex items-center justify-center font-bold text-muted-foreground text-xs">
                        #{i+1}
                      </div>
                      <div>
                        <p className="font-medium">{g.appliance_name}</p>
                        <p className="text-xs text-muted-foreground">{g.category} • {g.power_rating_watts}W</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-coral">{formatKwh(g.predicted_kwh)}</p>
                      <p className="text-xs text-muted-foreground">{g.avg_hours_per_day} hrs/day</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <div>
        <h2 className="text-xl font-bold mb-4">Appliances</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          
          <Card className="border-dashed border-2 bg-transparent shadow-none flex flex-col justify-center">
            <CardContent className="pt-6">
              <form onSubmit={handleAddAppliance} className="space-y-3">
                <Input placeholder="Appliance Name" required value={newName} onChange={e=>setNewName(e.target.value)} />
                <div className="flex gap-2">
                  <Input type="number" placeholder="Watts" required value={newWatts} onChange={e=>setNewWatts(e.target.value)} />
                  <Input type="number" placeholder="Age (yrs)" required value={newAge} onChange={e=>setNewAge(e.target.value)} />
                </div>
                <Button type="submit" className="w-full gap-2"><Plus className="size-4"/> Add Appliance</Button>
              </form>
            </CardContent>
          </Card>

          {appliances.map(a => (
            <Card key={a.id}>
              <CardHeader className="pb-3">
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-base">{a.appliance_name}</CardTitle>
                    <CardDescription>{a.category}</CardDescription>
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => handleDelete(a.id)} className="h-8 w-8 text-muted-foreground hover:text-destructive">
                    <Trash2 className="size-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2 mb-3">
                  <Badge variant="secondary">{a.power_rating_watts}W</Badge>
                  <Badge variant="outline">{a.age_years} yrs old</Badge>
                  {a.is_smart && <Badge variant="teal">Smart</Badge>}
                </div>
                <div className="text-sm flex items-center gap-1.5 text-muted-foreground">
                  <Clock className="size-4" /> {formatNum(a.avg_hours_per_day)} hrs/day avg
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
