# Changelog

## v1.2.0 (2025-07-21) - Stability and Documentation Update

### Improvements
- Enhanced documentation with more detailed troubleshooting guides
- Improved installer package with better cross-platform support
- Updated migration guide with more detailed instructions for existing users
- Refined error messages for better user experience
- Improved test coverage for critical components

### Bug Fixes
- Fixed minor issues with layout selection on first run
- Addressed edge cases in audio device fallback mechanism
- Fixed configuration migration issues from v1.0.0
- Resolved installer issues on certain Windows configurations

## v1.1.0 (2025-07-21) - UX Improvements Release

### New Features
- Added comprehensive QWERTY keyboard layout with all essential keys
- Added simple alphabetical layout for beginners
- Added layout metadata system to describe difficulty level and features
- Implemented automatic audio device fallback when primary device fails
- Added skip calibration option with sensible defaults
- Enhanced error handling with user-friendly messages and recovery options

### Improvements
- Improved first-run setup wizard with better guidance
- Enhanced error recovery in launcher to remain open when errors occur
- Added better default configuration values for new users
- Improved configuration validation and auto-repair functionality
- Enhanced audio calibration robustness with timeout handling and retry mechanisms
- Added layout selection system with smart defaults
- Added layout fallback mechanisms when custom layouts fail
- Improved cross-platform compatibility (Windows, macOS, Linux)
- Enhanced backward compatibility with existing user configurations

### Documentation
- Added getting started guide with step-by-step instructions
- Added troubleshooting documentation for common issues

### Bug Fixes
- Fixed issue with audio device detection on some systems
- Fixed calibration failures on certain hardware configurations
- Fixed layout loading errors with malformed JSON files
- Fixed configuration corruption recovery

## v1.0.0 (2025-01-15) - Initial Release

- Initial release of Switch Interface
- Basic keyboard layouts
- Audio switch detection
- Scanning keyboard interface
- Configuration system