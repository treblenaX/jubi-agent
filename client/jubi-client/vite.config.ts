import path from "path";
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

export default defineConfig({
	plugins: [
		tailwindcss(), // MUST come before sveltekit() for proper Tailwind v4 integration
		sveltekit()
	],
	resolve: {
		alias: {
			$lib: path.resolve("./src/lib"),
		},
	},
});
