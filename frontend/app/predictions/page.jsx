import ProductView from "../components/ProductViews";
export default async function Page({ searchParams }) {
  const query = await searchParams;
  return (
    <ProductView
      view="predictions"
      target={query?.target === "sprint" ? "sprint" : "race"}
    />
  );
}
