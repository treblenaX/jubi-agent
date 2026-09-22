export function cn(...inputs: string[]) {
    return inputs.filter(Boolean).join(" ");
}

export async function sendMessage(content: string, apiUrl: string): Promise<string> {
    try {
        const response = await fetch(`${apiUrl}?content=${encodeURIComponent(content)}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.text();
    } catch (error) {
        console.error("Error sending message:", error);
        throw error;
    }
}
