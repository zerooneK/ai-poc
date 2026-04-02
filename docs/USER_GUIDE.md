# AI Assistant — User Guide

## What is AI Assistant?

AI Assistant is an internal tool that helps you create documents and get answers to work-related questions by chatting with an AI. It understands both Thai and English. You can ask it to draft employment contracts, create invoices, write management reports, plan projects, or just have a conversation. The AI can also search the internet for current information and save documents in multiple formats.

## Getting Started

### Opening the Application

1. Open your web browser and go to **http://localhost:5000**
2. You will see the chat interface with a sidebar on the left and a message area in the center

### Starting a New Chat

1. Click **New Chat** in the sidebar to clear the conversation and start fresh
2. Type your message in the text box at the bottom of the screen
3. Click the **Send** button (or press Enter) to send your message

## Asking Questions

### General Questions

1. Type your question in the message box
2. Click **Send**
3. The AI will analyze your question and assign the best agent to answer it
4. You will see which agent is responding (shown as a colored badge above the response)
5. The response appears in real-time as the AI generates it

### Quick Shortcuts

The sidebar contains shortcut buttons for common tasks. Click any shortcut to automatically fill the message box with a suggested prompt. You can edit the text before sending.

## Working with Documents

### Generating a Document

1. Ask the AI to create a document. For example:
   - "ร่างสัญญาจ้างพนักงานชื่อ สมชาย ตำแหน่ง นักบัญชี เงินเดือน 35,000 บาท" (Draft an employment contract for Somchai, Accountant, salary 35,000 baht)
   - "สร้าง Invoice สำหรับลูกค้า ABC บริษัท จำกัด จำนวน 50,000 บาท" (Create an invoice for ABC Company, 50,000 baht)
2. The AI will generate the document and display it in the chat
3. When the document is ready, the input hint will change to remind you to save it

### Saving a Document

1. After the AI generates a document, type **บันทึก** (save) in the message box
2. A format selection window will appear
3. Choose your desired format:
   - **Markdown (.md)** — Plain text with formatting markers, good for editing
   - **Plain Text (.txt)** — Simple text without formatting
   - **Word (.docx)** — Microsoft Word document, good for sharing
   - **Excel (.xlsx)** — Spreadsheet format, best for tables and data
   - **PDF (.pdf)** — Fixed-layout document, good for printing
4. Click **บันทึกทั้งหมด** (Save All)
5. The file is saved to your workspace and appears in the file list on the sidebar

### Discarding a Document

1. If you do not want to save the document, type **ยกเลิก** (cancel)
2. The document will be discarded and you can send a new request
3. If you type an edit instruction while PM-generated files are still waiting to be saved, the system now only reminds you to save or discard first. It does not record that step as a real discard action.

### Editing a Document Before Saving

1. If you want to change the document before saving, type your edit instructions. For example:
   - "เพิ่มรายละเอียดเรื่องสวัสดิการประกันสุขภาพ" (Add details about health insurance benefits)
   - "เปลี่ยนเงินเดือนเป็น 40,000 บาท" (Change salary to 40,000 baht)
2. The AI will revise the document based on your instructions
3. The updated document replaces the previous one
4. You can continue editing or save when satisfied

## Multi-Agent Projects (PM Mode)

When your request involves multiple departments or document types, the Project Manager (PM) agent will break it into subtasks:

1. Ask for something that spans multiple areas. For example:
   - "สร้างเอกสาร onboarding พนักงานใหม่: สัญญาจ้าง + Invoice ค่าบริการ" (Create onboarding documents: employment contract + service invoice)
2. The PM agent will show a plan with subtasks, each assigned to a different agent
3. Each subtask runs sequentially and you can see the progress
4. When all subtasks are complete, you will see a prompt to save all files
5. Type **บันทึก** and select a format for each file individually
6. Click **บันทึกทั้งหมด** to save all files at once
7. If the PM agent cannot break the work into subtasks, the app now ends that response cleanly instead of leaving the interface stuck in a loading state.

## Viewing Files

### File List

The sidebar shows all files in your current workspace. Each file displays:
- File name
- File size
- Last modified date

The file list updates automatically when files are added or removed.
In the Next.js frontend, you can collapse the sidebar from the top header to free more space for the chat area. In collapsed mode, the same workspace, file, and session actions remain available in compact form.

### Opening a File

1. Click on a file name in the sidebar
2. The file content will be displayed in a preview panel
3. For PDF files, the file opens in a new browser tab

### Deleting a File

1. Click the delete icon next to a file in the sidebar
2. Confirm the deletion when prompted
3. The file is permanently removed from the workspace

## Managing Workspaces

### Switching Workspaces

1. Click the workspace selector in the sidebar
2. A list of available workspaces will appear
3. Click on a workspace to switch to it
4. Your conversation history will be reset for the new workspace
5. In the Next.js frontend, the workspace switch is now tied to your current browser session, so preview, file list, delete, and download all stay in the same workspace as your chat

### Creating a New Workspace

1. Click the workspace selector in the sidebar
2. Click **Create New Workspace**
3. Enter a name for the new workspace (letters, numbers, and underscores only)
4. Click **Create**
5. The new workspace becomes your active workspace

## Viewing History

### Job History Page

1. Go to **http://localhost:5000/history** in your browser
2. You will see a list of all previous requests (jobs)
3. Each entry shows:
   - The original message
   - Which agent handled it
   - The status (completed, error, or discarded)
   - Any files that were saved
4. Click on an entry to see the full details

### Sessions

Jobs are grouped into sessions. Each time you start a new chat, a new session begins. You can browse sessions from the history page to find previous conversations.

In the Next.js sidebar, clicking a session now restores all saved user and assistant messages from that session into the main chat area.

## Changing the Theme

1. Click the theme toggle icon (sun/moon) in the sidebar
2. The interface switches between dark mode and light mode
3. Your preference is saved and will be remembered next time you open the application

## Agent Types

The system automatically chooses the best agent for your request. Here is what each agent does:

| Agent | When It Is Used | Example Requests |
|---|---|---|
| **HR Agent** | Employment contracts, HR policies, job descriptions, employee emails | "ร่างสัญญาจ้าง", "เขียน JD สำหรับตำแหน่งนักพัฒนา" |
| **Accounting Agent** | Invoices, financial reports, expense reports | "สร้าง Invoice", "รายงานค่าใช้จ่าย" |
| **Manager Advisor** | Team feedback, headcount requests, management reports | "เขียน feedback ให้พนักงาน", "ขอเพิ่ม headcount" |
| **PM Agent** | Requests that need multiple agents working together | "สร้างเอกสาร onboarding ครบทุกแผนก" |
| **Chat Agent** | General questions, greetings, system questions | "สวัสดี", "ระบบทำอะไรได้บ้าง" |
| **Document Agent** | Document-specific tasks and formatting | "จัดรูปแบบเอกสารนี้ใหม่" |

## Web Search

When you ask about current information (laws, tax rates, market trends, news), the AI may automatically search the internet. Search results appear as clickable source links above the response.

## Tips

- **Be specific** — The more details you provide, the better the AI can help. Include names, amounts, dates, and specific requirements.
- **Use Thai or English** — Both languages are fully supported. You can mix them in the same conversation.
- **Edit before saving** — It is easier to ask the AI to revise a document than to edit the saved file manually.
- **Check the agent badge** — If the wrong agent is selected, rephrase your request to be more specific about the domain.
- **Save in the right format** — Use DOCX for documents you need to edit in Word, PDF for final versions, and XLSX for data tables.

## Frequently Asked Questions

**Q: The AI is taking a long time to respond. What should I do?**
A: Complex document generation can take 30-90 seconds. If it takes longer than 2 minutes, try sending your message again. The system has a timeout of 120 seconds.

**Q: Can I use this on my phone?**
A: The interface is designed for desktop browsers. It may work on mobile but is not optimized for small screens.

**Q: Where are my saved files stored?**
A: Files are saved in the `workspace/` folder on the server. You can switch between different workspace folders using the workspace selector in the sidebar.

**Q: Can I export a document after saving it?**
A: Yes. You can download saved files directly from the file list in the sidebar. You can also ask the AI to regenerate the document in a different format.

**Q: What happens if I close the browser while a document is being generated?**
A: The generation will continue on the server, but you will not see the result. When you reopen the application, you can check the history page to see if the job completed.

**Q: Can multiple people use this at the same time?**
A: Yes. Each user session has its own isolated workspace, and the file APIs now use the same session scope as chat generation. If one person switches workspaces, other sessions continue using their own workspace independently.

## Getting Help

If you encounter issues or have questions about the system, check the history page at **http://localhost:5000/history** for details about previous requests. For technical issues, contact the development team.
- In the Next.js sidebar, each saved session now has a delete button so you can remove that session and its chat history directly from the UI.
- The Next.js sidebar now refreshes session history automatically after you send a message and when the assistant reply completes.
- The Next.js interface now includes a top navbar with a "สร้างเซสชันใหม่" button that opens a fresh empty chat session.
- The quick-action cards on the empty chat screen are now clickable and send preset starter prompts.
- Assistant replies in the Next.js chat now appear progressively while the response is streaming.
- Switching between saved sessions now highlights the target immediately, shows a loading indicator when needed, and restores previously opened sessions faster from local cache.
- The Next.js UI now has a cleaner layout and a theme toggle in the top bar. Your light/dark choice is saved in the browser and restored automatically on reload.
- The header controls and welcome panel have been tightened so the main chat area has more visual breathing room.
- The top-bar theme switch has been corrected so the toggle knob stays aligned properly in the redesigned header.
- The workspace selection dialog now uses a stronger backdrop and an opaque panel so page content behind it is no longer visible through the modal.
- In the Next.js chat, when a generated document is waiting to be saved, typing `save` or `บันทึก` now opens the file-format picker first. After confirmation, the file is saved and the sidebar file list refreshes automatically.
- Clicking a selected session in the Next.js sidebar can now restore its messages again if the current chat view was cleared locally.
- The save-format dialog now also uses a stronger backdrop and a solid dialog surface, so text behind it is no longer visible through the modal.
- The latest selected session now restores correctly even if the visible chat area was previously cleared, because empty frontend state no longer overwrites the saved session cache.
- Backend request handling is now stricter for history limits and save-related chat payloads, reducing cases where malformed client input could produce incorrect job state or server errors.
- Long-running backend behavior is now safer: session workspace mappings are cleaned up when sessions are deleted, and file-change subscriptions send heartbeats during idle periods to reduce stuck background listeners.
