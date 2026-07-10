export interface Chat {
  id: string;
  name: string;
  initials: string;
  color: string;
  lastMessage: string;
  time: string;
  unread: number;
  pinned?: boolean;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  time: string;
}

export interface AIModel {
  id: string;
  name: string;
  provider: string;
  color: string;
  initials: string;
  enabled: boolean;
  skill?: string;
  avatar_url?: string | null;
}

export const chats: Chat[] = [
  {
    id: "1",
    name: "GPT-4o",
    initials: "G",
    color: "#10a37f",
    lastMessage: "Sure! Here's a summary of quantum computing...",
    time: "12:30",
    unread: 2,
    pinned: true,
  },
  {
    id: "2",
    name: "Claude Sonnet",
    initials: "C",
    color: "#D97706",
    lastMessage: "I can help you write that email. What's the context?",
    time: "11:45",
    unread: 0,
    pinned: true,
  },
  {
    id: "3",
    name: "Gemini Pro",
    initials: "G",
    color: "#4285F4",
    lastMessage: "The recipe calls for 2 cups of flour and...",
    time: "Yesterday",
    unread: 0,
  },
  {
    id: "4",
    name: "Llama 3.1",
    initials: "L",
    color: "#7C3AED",
    lastMessage: "Here are 5 ways to improve your productivity...",
    time: "Mon",
    unread: 0,
  },
  {
    id: "5",
    name: "Mistral Large",
    initials: "M",
    color: "#EF4444",
    lastMessage: "The code looks good! I've added error handling.",
    time: "Sun",
    unread: 0,
  },
  {
    id: "6",
    name: "DeepSeek V3",
    initials: "D",
    color: "#0EA5E9",
    lastMessage: "Mathematical proof of Fermat's Last Theorem...",
    time: "Sat",
    unread: 5,
  },
  {
    id: "7",
    name: "Perplexity",
    initials: "P",
    color: "#6366F1",
    lastMessage: "Based on recent AI news, the landscape has shifted...",
    time: "Fri",
    unread: 0,
  },
  {
    id: "8",
    name: "Qwen 2.5",
    initials: "Q",
    color: "#F59E0B",
    lastMessage: "在中文方面，我可以为您提供更准确的翻译和解释。",
    time: "Thu",
    unread: 0,
  },
];

export const messagesByChat: Record<string, Message[]> = {
  "1": [
    { id: "m1", role: "user", content: "Explain quantum computing in simple terms", time: "12:28" },
    {
      id: "m2",
      role: "assistant",
      content:
        "Quantum computing harnesses the principles of quantum mechanics to process information in fundamentally different ways than classical computers.\n\nWhile classical computers use bits (0 or 1), quantum computers use qubits that can exist in multiple states simultaneously — a phenomenon called superposition.\n\nKey concepts:\n• Superposition — A qubit can be 0, 1, or both at once\n• Entanglement — Qubits can be linked so the state of one instantly affects another\n• Interference — Quantum algorithms amplify correct answers and cancel wrong ones",
      time: "12:29",
    },
    { id: "m3", role: "user", content: "Can you give a practical example?", time: "12:30" },
    {
      id: "m4",
      role: "assistant",
      content:
        "Sure! Here's a practical example:\n\nImagine you're looking for a specific book in a massive library with millions of shelves. A classical computer checks each shelf one by one. A quantum computer can check all shelves simultaneously, dramatically speeding up the search.\n\nThis is why quantum computers excel at:\n• Breaking encryption (Shor's algorithm)\n• Drug discovery simulations\n• Optimization problems in logistics and finance\n• Weather and climate modeling",
      time: "12:30",
    },
  ],
  "2": [
    { id: "m1", role: "user", content: "Help me write a professional email to decline a job offer", time: "11:44" },
    {
      id: "m2",
      role: "assistant",
      content:
        "I can help you write that email. What's the context?\n\nTo craft the best response, could you tell me:\n1. The company and role you're declining\n2. The reason (if you'd like to include one)\n3. Whether you want to leave the door open for future opportunities\n4. Your preferred tone (formal vs. warm and conversational)",
      time: "11:45",
    },
  ],
  "3": [
    { id: "m1", role: "user", content: "Give me a classic chocolate cake recipe", time: "14:20" },
    {
      id: "m2",
      role: "assistant",
      content:
        "The recipe calls for 2 cups of flour and the following ingredients:\n\nFor the cake:\n• 2 cups all-purpose flour\n• 2 cups sugar\n• ¾ cup cocoa powder\n• 2 tsp baking soda, 1 tsp salt\n• 2 eggs, 1 cup buttermilk\n• 1 cup strong black coffee\n• ½ cup vegetable oil, 1 tsp vanilla\n\nFor the frosting:\n• 1 cup butter\n• 3 cups powdered sugar\n• ½ cup cocoa powder\n• ¼ cup heavy cream",
      time: "14:21",
    },
  ],
  "4": [
    { id: "m1", role: "user", content: "What are 5 productivity tips for developers?", time: "09:15" },
    {
      id: "m2",
      role: "assistant",
      content:
        "Here are 5 ways to improve your productivity as a developer:\n\n1. Use the Pomodoro Technique — 25 min focused work, 5 min break\n2. Master your editor shortcuts — save hours every week\n3. Automate repetitive tasks with scripts and aliases\n4. Keep a daily journal of blockers and wins\n5. Do deep work in the morning when focus is highest",
      time: "09:16",
    },
  ],
  "5": [
    { id: "m1", role: "user", content: "Review this Python code for bugs", time: "16:30" },
    {
      id: "m2",
      role: "assistant",
      content:
        "The code looks good! I've added error handling for edge cases.\n\nIssues found:\n• Line 12: Possible ZeroDivisionError — add a check before dividing\n• Line 28: The variable 'result' might be undefined if the condition is false\n• Line 45: This regex pattern doesn't handle unicode characters\n\nSuggested fixes have been inline commented.",
      time: "16:32",
    },
  ],
  "6": [
    { id: "m1", role: "user", content: "Can you explain Fermat's Last Theorem?", time: "20:10" },
    {
      id: "m2",
      role: "assistant",
      content:
        "Mathematical proof of Fermat's Last Theorem:\n\nThe theorem states: No three positive integers a, b, c can satisfy:\naⁿ + bⁿ = cⁿ for any integer n > 2\n\nFermat wrote this in 1637, but the proof wasn't found until 1995 when Andrew Wiles proved it after 7 years of secret work, using elliptic curves and modular forms.",
      time: "20:11",
    },
    { id: "m3", role: "user", content: "What's the connection to elliptic curves?", time: "20:15" },
    {
      id: "m4",
      role: "assistant",
      content:
        "Great question! The Taniyama-Shimura conjecture connects every elliptic curve to a modular form. Wiles proved this conjecture for semistable elliptic curves.\n\nThe key insight: if Fermat's theorem were false, there would exist an elliptic curve (the Frey curve) that couldn't be modular — contradicting the conjecture Wiles had just proved.\n\nIt's a beautiful example of how seemingly unrelated branches of math are deeply connected.",
      time: "20:17",
    },
    { id: "m5", role: "user", content: "Any resources to learn more?", time: "20:20" },
    {
      id: "m6",
      role: "assistant",
      content:
        "Here are excellent resources:\n\nFor beginners:\n• \"Fermat's Enigma\" by Simon Singh — an accessible and engaging narrative\n• YouTube: 3Blue1Brown's number theory series\n\nFor intermediate:\n• \"A First Course in Modular Forms\" by Diamond & Shurman\n\nFor advanced:\n• Wiles' original 1995 paper in Annals of Mathematics",
      time: "20:21",
    },
  ],
  "7": [],
  "8": [],
};

export const aiModels: AIModel[] = [
  { id: "gpt-4o", name: "GPT-4o", provider: "OpenAI", color: "#10a37f", initials: "G", enabled: true },
  { id: "claude-sonnet", name: "Claude Sonnet 4.6", provider: "Anthropic", color: "#D97706", initials: "C", enabled: true },
  { id: "gemini-pro", name: "Gemini 1.5 Pro", provider: "Google", color: "#4285F4", initials: "G", enabled: true },
  { id: "llama-3.1", name: "Llama 3.1 70B", provider: "Meta", color: "#7C3AED", initials: "L", enabled: false },
  { id: "mistral-large", name: "Mistral Large 2", provider: "Mistral AI", color: "#EF4444", initials: "M", enabled: true },
  { id: "deepseek-v3", name: "DeepSeek V3", provider: "DeepSeek", color: "#0EA5E9", initials: "D", enabled: true },
  { id: "perplexity", name: "Perplexity Sonar", provider: "Perplexity AI", color: "#6366F1", initials: "P", enabled: false },
  { id: "qwen-2.5", name: "Qwen 2.5 72B", provider: "Alibaba Cloud", color: "#F59E0B", initials: "Q", enabled: false },
];
