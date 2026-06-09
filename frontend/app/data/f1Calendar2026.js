export const F1_2026_CALENDAR = [
  { round: 1, name: "Australian Grand Prix", circuit: "Albert Park", city: "Melbourne", country: "Australia", start: "2026-03-06", end: "2026-03-08", sprint: false },
  { round: 2, name: "Chinese Grand Prix", circuit: "Shanghai International Circuit", city: "Shanghai", country: "China", start: "2026-03-13", end: "2026-03-15", sprint: true },
  { round: 3, name: "Japanese Grand Prix", circuit: "Suzuka Circuit", city: "Suzuka", country: "Japan", start: "2026-03-27", end: "2026-03-29", sprint: false },
  { round: 4, name: "Bahrain Grand Prix", circuit: "Bahrain International Circuit", city: "Sakhir", country: "Bahrain", start: "2026-04-10", end: "2026-04-12", sprint: false },
  { round: 5, name: "Canadian Grand Prix", circuit: "Circuit Gilles Villeneuve", city: "Montreal", country: "Canada", start: "2026-05-22", end: "2026-05-24", sprint: true },
  { round: 6, name: "Monaco Grand Prix", circuit: "Circuit de Monaco", city: "Monte Carlo", country: "Monaco", start: "2026-06-05", end: "2026-06-07", sprint: false },
  { round: 7, name: "Barcelona Grand Prix", circuit: "Circuit de Barcelona-Catalunya", city: "Barcelona", country: "Spain", start: "2026-06-12", end: "2026-06-14", sprint: false },
  { round: 8, name: "Austrian Grand Prix", circuit: "Red Bull Ring", city: "Spielberg", country: "Austria", start: "2026-06-26", end: "2026-06-28", sprint: false },
  { round: 9, name: "British Grand Prix", circuit: "Silverstone Circuit", city: "Silverstone", country: "Great Britain", start: "2026-07-03", end: "2026-07-05", sprint: true },
  { round: 10, name: "Belgian Grand Prix", circuit: "Circuit de Spa-Francorchamps", city: "Spa-Francorchamps", country: "Belgium", start: "2026-07-17", end: "2026-07-19", sprint: false },
  { round: 11, name: "Hungarian Grand Prix", circuit: "Hungaroring", city: "Budapest", country: "Hungary", start: "2026-07-24", end: "2026-07-26", sprint: false },
  { round: 12, name: "Dutch Grand Prix", circuit: "Circuit Zandvoort", city: "Zandvoort", country: "Netherlands", start: "2026-08-21", end: "2026-08-23", sprint: true },
  { round: 13, name: "Italian Grand Prix", circuit: "Autodromo Nazionale Monza", city: "Monza", country: "Italy", start: "2026-09-04", end: "2026-09-06", sprint: false },
  { round: 14, name: "Madrid Grand Prix", circuit: "Madring", city: "Madrid", country: "Spain", start: "2026-09-11", end: "2026-09-13", sprint: false },
  { round: 15, name: "Azerbaijan Grand Prix", circuit: "Baku City Circuit", city: "Baku", country: "Azerbaijan", start: "2026-09-24", end: "2026-09-26", sprint: false },
  { round: 16, name: "Singapore Grand Prix", circuit: "Marina Bay Street Circuit", city: "Singapore", country: "Singapore", start: "2026-10-09", end: "2026-10-11", sprint: true },
  { round: 17, name: "United States Grand Prix", circuit: "Circuit of The Americas", city: "Austin", country: "United States", start: "2026-10-23", end: "2026-10-25", sprint: false },
  { round: 18, name: "Mexico City Grand Prix", circuit: "Autodromo Hermanos Rodriguez", city: "Mexico City", country: "Mexico", start: "2026-10-30", end: "2026-11-01", sprint: false },
  { round: 19, name: "Sao Paulo Grand Prix", circuit: "Interlagos", city: "Sao Paulo", country: "Brazil", start: "2026-11-06", end: "2026-11-08", sprint: false },
  { round: 20, name: "Las Vegas Grand Prix", circuit: "Las Vegas Strip Circuit", city: "Las Vegas", country: "United States", start: "2026-11-19", end: "2026-11-21", sprint: false },
  { round: 21, name: "Qatar Grand Prix", circuit: "Lusail International Circuit", city: "Lusail", country: "Qatar", start: "2026-11-27", end: "2026-11-29", sprint: false },
  { round: 22, name: "Abu Dhabi Grand Prix", circuit: "Yas Marina Circuit", city: "Abu Dhabi", country: "United Arab Emirates", start: "2026-12-04", end: "2026-12-06", sprint: false },
];

export function activeCalendarRound(now = new Date()) {
  const today = new Date(now.toISOString().slice(0, 10));
  return F1_2026_CALENDAR.find((race) => new Date(`${race.end}T23:59:59Z`) >= today) || F1_2026_CALENDAR[F1_2026_CALENDAR.length - 1];
}
