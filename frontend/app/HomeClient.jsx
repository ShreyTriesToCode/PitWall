"use client";
import ProductView from "./components/ProductViews";
export default function HomeClient({ initialData }) {
  return <ProductView view="home" initialData={initialData} />;
}
