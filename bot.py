import os
from infer_rvc_python import BaseLoader
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler

# States for the conversation
FILE_MODEL, FILE_INDEX, PITCH_LVL = range(3)

# Initialize the converter
converter = BaseLoader(only_cpu=False, hubert_path=None, rmvpe_path=None)

# Function to configure and convert audio file
def convert_audio(file_path: str, file_model: str, file_index: str, pitch_lvl: str, pitch_algo: str) -> str:
    model_name = file_model.split("/")[-1].split(".pth")[0]
    speakers_list = [model_name]

    converter.apply_conf(
        tag=model_name,
        file_model=file_model,
        pitch_algo=pitch_algo,
        pitch_lvl=int(pitch_lvl),
        file_index=file_index,
        index_influence=0.66,
        respiration_median_filtering=3,
        envelope_ratio=0.25,
        consonant_breath_protection=0.33
    )

    result = converter(
        file_path,
        speakers_list,
        overwrite=False,
        parallel_workers=4
    )
    
    return result  # Path to the converted file

# Command handler to start the bot
def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Hi! Send the path to your model file (.pth):')
    return FILE_MODEL

def file_model_handler(update: Update, context: CallbackContext) -> int:
    context.user_data['file_model'] = update.message.text
    update.message.reply_text('Got it! Now send the path to your index file:')
    return FILE_INDEX

def file_index_handler(update: Update, context: CallbackContext) -> int:
    context.user_data['file_index'] = update.message.text
    update.message.reply_text('Great! Finally, provide the pitch level (e.g., 0, 12, -12):')
    return PITCH_LVL

def pitch_lvl_handler(update: Update, context: CallbackContext) -> int:
    context.user_data['pitch_lvl'] = update.message.text
    update.message.reply_text('Now send the audio file you want to convert:')
    return ConversationHandler.END

def handle_audio(update: Update, context: CallbackContext) -> None:
    audio_file = update.message.audio.get_file()
    file_path = audio_file.download()
    update.message.reply_text('Converting your file...')

    # Retrieve user-provided parameters
    file_model = context.user_data['file_model']
    file_index = context.user_data['file_index']
    pitch_lvl = context.user_data['pitch_lvl']
    pitch_algo = "rmvpe+"

    # Convert the audio file
    result_path = convert_audio(file_path, file_model, file_index, pitch_lvl, pitch_algo)
    
    # Send back the converted file
    update.message.reply_audio(audio=open(result_path, 'rb'))
    
    # Cleanup
    os.remove(file_path)  # Remove the original uploaded file
    os.remove(result_path)  # Remove the converted file

def main() -> None:
    # Create the Updater and pass it your bot's token.
    updater = Updater("YOUR_TELEGRAM_BOT_TOKEN", use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Conversation handler to guide user through inputs
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FILE_MODEL: [MessageHandler(Filters.text & ~Filters.command, file_model_handler)],
            FILE_INDEX: [MessageHandler(Filters.text & ~Filters.command, file_index_handler)],
            PITCH_LVL: [MessageHandler(Filters.text & ~Filters.command, pitch_lvl_handler)],
        },
        fallbacks=[],
    )

    # Register the conversation handler
    dp.add_handler(conv_handler)

    # Register the audio file handler
    dp.add_handler(MessageHandler(Filters.audio, handle_audio))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you send a signal to stop (Ctrl+C)
    updater.idle()

if __name__ == '__main__':
    main()
