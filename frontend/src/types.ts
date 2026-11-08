export interface Variant {
  id: number;
  sku: string;
  size: string;
  color: string;
  color_hex: string;
  price: string;
  available: number;
}
export interface Product {
  id: number;
  name: string;
  slug: string;
  category: string;
  category_slug: string;
  description: string;
  characteristics: Record<string, string>;
  badge: string;
  is_new: boolean;
  price: string;
  images: { url: string; alt: string }[];
  variants: Variant[];
}
export interface CatalogResponse {
  count: number;
  next: number | null;
  results: Product[];
}
export interface Facets {
  categories: { name: string; slug: string }[];
  sizes: string[];
  colors: { color: string; color_hex: string }[];
  max_price: number;
}
export interface Store {
  brand: string;
  tagline: string;
  announcement: string;
  hero_title: string;
  hero_text: string;
  hero_image: string;
  about_title: string;
  about_text: string;
  about_image: string;
  email: string;
  phone: string;
  address: string;
  legal_details: string;
  pages: { slug: string; title: string }[];
}
export interface CartLine {
  variant_id: number;
  quantity: number;
  product: Product;
}
export interface Quote {
  subtotal: string;
  discount: string;
  shipping_cost: string;
  total: string;
  delivery_days: string;
}
export interface City {
  code: number;
  city: string;
  region?: string;
}
export interface Pickup {
  code: string;
  name: string;
  address: string;
  hours: string;
  city_code: number;
}
export interface Order extends Quote {
  number: string;
  token: string;
  status: string;
  status_label: string;
  created_at: string;
  expires_at: string;
  delivery_address: string;
  delivery_method: string;
  tracking: string;
  items: {
    name: string;
    size: string;
    color: string;
    quantity: number;
    price: string;
    total: string;
  }[];
}
