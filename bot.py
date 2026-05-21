import os
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler
)
from sqlalchemy import Column, Integer, String, func, update
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from enum import Enum
from datetime import datetime, timezone

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
db = SessionLocal()


TOKEN = os.getenv("TOKEN")

class Status(Enum):
    Active = "Active"
    Paused = "Paused"
    Completed = "Completed"
    NotStarted = "Not_Started"

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    status = Column(String(20), default=Status.NotStarted.value)
    timestamp = Column(Integer, default=lambda: int(datetime.now(timezone.utc).timestamp()))

async def button_handler(update: Update, context : ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "projects":
        await projects(update, context)
    elif data == "ideas":
        await query.edit_message_text("These feature will be added soon!")
    elif data == "ongoing":
        await Ongoing(update, context)
    elif data == "update":
        await query.edit_message_text("You clicked on Update!")
    elif data == "newidea":
        await query.edit_message_text("These feature will be added soon!")
    elif data == "goback":
        await start(update, context)
    elif data.startswith("update_status:"):
        proj_id = int(data.split(":")[1])
        project = db.query(Project).filter_by(id=proj_id).first()
        if project:
            keyboard = [
                [InlineKeyboardButton("🟢 Active", callback_data=f"set_status:{proj_id}:Active"),
                InlineKeyboardButton("🟡 Paused", callback_data=f"set_status:{proj_id}:Paused")],
                [InlineKeyboardButton("✅ Completed", callback_data=f"set_status:{proj_id}:Completed"),
                InlineKeyboardButton("⚪ Not Started", callback_data=f"set_status:{proj_id}:Not_Started")],
                [InlineKeyboardButton("⬅️ Go Back", callback_data="goback")]
            ]
            await query.edit_message_text(f"Choose a new status for the project: {project.name}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text("Project not found.")
    elif data.startswith("set_status:"):
        _, proj_id, new_status = data.split(":")
        proj_id = int(proj_id)
        project = db.query(Project).filter_by(id=proj_id).first()
        keyboard = [[InlineKeyboardButton("⬅️ Go Back", callback_data="goback")]]
        if project:
            project.status = new_status
            db.commit()
            await update.callback_query.edit_message_text(f"Project status updated to *{new_status}*.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.callback_query.edit_message_text("Project not found.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(
                "📁 Projects",
                callback_data="projects"
            ),
            InlineKeyboardButton(
                "💡 Ideas",
                callback_data="ideas"
            )
        ],
        [
            InlineKeyboardButton(
                "📅 Ongoing Tasks",
                callback_data="ongoing"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 Update",
                callback_data="update"
            ),
            InlineKeyboardButton(
                "📝 Add Idea",
                callback_data="newidea"
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    message = """
    🚀 *Welcome to Your Productivity Bot*

    Your personal space to:
    • Save ideas instantly
    • Track projects
    • Manage tasks
    • Stay focused

    Use the buttons below to navigate.
    """
    if update.message:
        await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
    elif update.callback_query:
        query = update.callback_query
        await query.edit_message_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
    
async def Ongoing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    keyboard = [[InlineKeyboardButton("⬅️ Go Back", callback_data="goback")]]
    projects = db.query(Project).filter_by(status = Status.Active.value).all()
    if not projects:
        message = "📭 *No ongoing tasks found.*\n\nUse `/new <project_name>` to create a new project and set it to active."
    else:
        message = (
            "📅 *Ongoing Tasks*\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
        )
        for sno, proj in enumerate(projects, start=1):
            message += f"`#{sno:02d}` 🚀 *{proj.name}* `[ID: {proj.id}]`\n"
            
        message += "\n━━━━━━━━━━━━━━━━━━━\n"
        message += f"📊 Total Active: *{len(projects)} tasks*"

    if update.message:
        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif update.callback_query:
        query = update.callback_query
        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text(
            "Please provide a project name. Usage: /new <project_name>"
        )
        return
    
    project_name = " ".join(context.args)
    isduplicate = db.query(Project).filter(func.upper(Project.name) == project_name.upper()).first()
    if isduplicate:
        await update.message.reply_text(
            f"A project with the name '{project_name}' already exists. Please choose a different name."
        )
        return
    newproj = Project(name=project_name)
    db.add(newproj)
    db.commit()
    await update.message.reply_text(
        f"Project '{project_name}' created successfully!"
    )

async def projects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    projects_list = db.query(Project).all()
    keyboard = []

    if not projects_list:
        response = (
            "📭 *No projects found.*\n\n"
            "Use `/new <project_name>` to spin one up."
        )
    else:
        response = "📁 *Your active project space*\n"
        response += "_Click a project button below to modify its status_\n"
        response += "━━━━━━━━━━━━━━━━━━━\n\n"
        
        for sno, proj in enumerate(projects_list, start=1):
            status_lower = proj.status.lower() if proj.status else ""
            if status_lower == "completed":
                emoji = "🟢"
            elif status_lower == "ongoing":
                emoji = "🔵"
            elif status_lower == "paused":
                emoji = "⏸️"
            elif status_lower == "not_started":
                emoji = "⚪"
                
            response += f"`#{sno:02d}` {emoji} *{((proj.name).upper())}* `[STATUS: {proj.status}]`\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"⚙️ Manage #{sno:02d}: {(proj.name).upper()}",
                    callback_data=f"update_status:{proj.id}"
                )
            ])  
            
        response += "\n━━━━━━━━━━━━━━━━━━━\n"
        response += f"📊 Total tracking: *{len(projects_list)} elements*"

    keyboard.append([InlineKeyboardButton("⬅️ Go Back", callback_data="goback")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            response,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    elif update.message:
        await update.message.reply_text(
            response,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text(
            "Please provide a project ID to delete. Usage: /del <project_id>"
        )
        return
    project_id = context.args[0]
    project = db.query(Project).filter_by(id=int(project_id)).first()
    if not project:
        await update.message.reply_text("Project not found.")
        return

    db.delete(project)
    db.commit()
    await update.message.reply_text(f"Project '{project.name}' deleted successfully!")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "🆘 *Help Guide*\n\n"
        "Here are the commands you can use:\n\n"
        "• `/start` - Show the main menu\n"
        "• `/new <project_name>` - Create a new project\n"
        "• `/projects` - List all projects and manage their status\n"
        "• `/ongoing` - View all active projects\n"
        "• `/del <project_id>` - Delete a project by its ID\n"
        "• Click on project buttons to update their status or view details.\n\n"
        "For any further assistance, feel free to reach out!"
    )
    await update.message.reply_text(message, parse_mode="Markdown")

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(CommandHandler("new", new))
app.add_handler(CommandHandler("projects", projects))
app.add_handler(CommandHandler("ongoing", Ongoing))
app.add_handler(CommandHandler("del", delete))
app.add_handler(CommandHandler("help", help))

print("Bot Running...")

Base.metadata.create_all(engine)
PORT = int(os.getenv('PORT', 8443))
WEBHOOK_URL = os.getenv('WEBHOOK_URL')


async def main():
    print("Starting bot...")

    await app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="telegram_webhook",
        webhook_url=f"{WEBHOOK_URL}/telegram_webhook",
        secret_token=os.getenv("SECRET")
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print("ERROR:", e)

