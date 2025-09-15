# 🤝 Contributing to Plex File Renamer

Thanks for your interest in contributing! This project welcomes help from the community.

## 🚀 Quick Setup

```bash
# Fork the repository on GitHub first, then:

git clone https://github.com/YOUR-USERNAME/plex-file-namer.git
cd plex-file-namer

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set your TMDb API key for testing
export TMDB_API_KEY="your_test_api_key"

# Test the script
python plex_file_renamer.py test_files/ --dry-run
```

## 📝 How to Contribute

### 🐛 Bug Reports
If something doesn't work:
1. Check if there's already an issue for it
2. Create a new issue with:
   - What you expected to happen
   - What actually happened
   - The exact command you ran
   - Sample filenames (remove personal info)
   - Any error messages

### 💡 Feature Ideas
Have an idea for improvement?
1. Create an issue describing the feature
2. Explain why it would be useful
3. Give examples of how it would work

### 🔧 Code Changes
Want to fix something or add a feature?

1. **Create a branch:**
   ```bash
   git checkout -b fix-something-cool
   ```

2. **Make your changes**

3. **Test it works:**
   ```bash
   # Test with different file types
   python plex_file_renamer.py test_files/ --dry-run
   
   # Test actual renaming
   python plex_file_renamer.py test_files/ --rename
   
   # Test reverting
   python plex_file_renamer.py test_files/ --revert
   ```

4. **Submit a pull request**

## 🎯 Areas We Need Help With

- **🎬 More filename patterns** - Add support for new naming styles
- **🔍 Better detection** - Improve movie vs TV show detection
- **🌐 Internationalization** - Support for non-English titles
- **📚 Documentation** - Improve examples and troubleshooting
- **🧪 Testing** - Test with more file types and edge cases
- **🐛 Bug fixes** - Fix issues people report

## 📋 Code Guidelines

Keep it simple:
- Follow the existing code style
- Add comments for tricky parts
- Test your changes with real files
- Don't break existing functionality

## 🎉 Recognition

Contributors get mentioned in:
- The README
- Release notes
- Our thanks! 🙏

## ❓ Need Help?

- Check existing issues for similar problems
- Create an issue if you're stuck
- We're friendly and happy to help!

---

**Thanks for making Plex File Renamer better! 🎬**