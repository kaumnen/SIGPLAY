# Requirements Document

## Introduction

The Floppy Mix feature enables users to create custom audio mixes by selecting tracks from their library and providing natural language instructions for how those tracks should be mixed together. The system leverages the Strands Agents LLM system to interpret user intent and uses the Pedalboard audio processing library to perform professional-quality mixing operations including tempo adjustment, EQ manipulation, and gapless transitions. The resulting mix can be previewed immediately or saved as a new audio file.

## Glossary

- **Floppy Mix**: The complete feature system that allows users to create AI-generated audio mixes
- **Mix Dialog**: A modal popup interface where users configure and initiate mix creation
- **Track Selection Panel**: The left side of the Mix Dialog showing available tracks for mixing
- **Instructions Panel**: The right side of the Mix Dialog where users enter natural language mixing instructions
- **Strands Agents**: The LLM system that interprets user instructions and generates mixing commands
- **Pedalboard**: Python audio processing library used to apply effects and transformations to audio
- **Mix File**: The output audio file generated from the mixing process
- **Gapless Playback**: Audio playback where tracks transition without silence between them
- **BPM**: Beats Per Minute, the tempo of a musical track
- **Audio Player Service**: The existing service in SIGPLAY that handles audio playback
- **Music Library Service**: The existing service that manages the track collection

## Requirements

### Requirement 1

**User Story:** As a user, I want to open an AI DJ mixing interface from the main application, so that I can create custom mixes without leaving the player.

#### Acceptance Criteria

1. WHEN a user presses the 'd' key THEN the SIGPLAY Application SHALL display the Mix Dialog as a modal overlay
2. WHEN the Mix Dialog is displayed THEN the SIGPLAY Application SHALL maintain the current playback state in the background
3. WHEN a user presses the Escape key while the Mix Dialog is open THEN the SIGPLAY Application SHALL close the Mix Dialog and return to the main interface
4. WHEN the Mix Dialog is closed THEN the SIGPLAY Application SHALL restore focus to the previously active view

### Requirement 2

**User Story:** As a user, I want to select multiple tracks from my library for mixing, so that I can specify which songs should be included in the AI-generated mix.

#### Acceptance Criteria

1. WHEN the Mix Dialog opens THEN the Track Selection Panel SHALL display all tracks from the Music Library Service
2. WHEN a user navigates the track list using 'j' and 'k' keys THEN the Track Selection Panel SHALL move the selection cursor accordingly
3. WHEN a user presses the Space key on a track THEN the Track Selection Panel SHALL toggle that track's selection state
4. WHEN a track is selected THEN the Track Selection Panel SHALL display a visual indicator next to that track
5. WHEN a user selects multiple tracks THEN the Track Selection Panel SHALL maintain all selections simultaneously
6. WHEN no tracks are selected THEN the Track Selection Panel SHALL display a message indicating that at least one track must be selected

### Requirement 3

**User Story:** As a user, I want to provide natural language instructions for how tracks should be mixed, so that I can describe my desired output without technical audio engineering knowledge.

#### Acceptance Criteria

1. WHEN the Mix Dialog opens THEN the Instructions Panel SHALL display a text input area for mixing instructions
2. WHEN a user types in the text input area THEN the Instructions Panel SHALL accept and display the text input
3. WHEN the text input area is empty THEN the Instructions Panel SHALL display placeholder text with example instructions
4. WHEN a user enters instructions THEN the Instructions Panel SHALL support multi-line text input
5. WHERE the Instructions Panel displays placeholder text THEN the placeholder SHALL include examples such as "more bass in songs, all in 180 bpm rhythm with gapless play"

### Requirement 4

**User Story:** As a user, I want to initiate the mixing process with my selected tracks and instructions, so that the AI can generate my custom mix.

#### Acceptance Criteria

1. WHEN a user presses the Enter key with at least one track selected and instructions provided THEN the AI DJ Mixer SHALL initiate the mixing process
2. WHEN the mixing process starts THEN the AI DJ Mixer SHALL display a progress indicator showing the current operation
3. WHEN the mixing process is active THEN the AI DJ Mixer SHALL prevent the user from modifying track selections or instructions
4. IF a user attempts to start mixing with no tracks selected THEN the AI DJ Mixer SHALL display an error notification and prevent the operation
5. IF a user attempts to start mixing with empty instructions THEN the AI DJ Mixer SHALL display an error notification and prevent the operation

### Requirement 5

**User Story:** As a system, I want to send user instructions to the Strands Agents LLM system, so that natural language can be converted into executable audio processing commands.

#### Acceptance Criteria

1. WHEN the mixing process starts THEN the AI DJ Mixer SHALL send the user instructions to the Strands Agents MCP server
2. WHEN communicating with Strands Agents THEN the AI DJ Mixer SHALL include context about available audio processing capabilities
3. WHEN Strands Agents returns a response THEN the AI DJ Mixer SHALL parse the response into a structured mixing plan
4. IF the Strands Agents MCP server is unavailable THEN the AI DJ Mixer SHALL display an error notification and abort the mixing process
5. IF Strands Agents returns an error or invalid response THEN the AI DJ Mixer SHALL display a user-friendly error message

### Requirement 6

**User Story:** As a system, I want to apply audio processing operations using Pedalboard, so that I can transform tracks according to the AI-generated mixing plan.

#### Acceptance Criteria

1. WHEN the AI DJ Mixer receives a mixing plan THEN the AI DJ Mixer SHALL load the selected audio files using Pedalboard
2. WHEN applying tempo adjustments THEN the AI DJ Mixer SHALL use Pedalboard to change track BPM without altering pitch
3. WHEN applying EQ adjustments THEN the AI DJ Mixer SHALL use Pedalboard to modify frequency content
4. WHEN creating gapless transitions THEN the AI DJ Mixer SHALL use Pedalboard to crossfade between tracks
5. WHEN processing is complete THEN the AI DJ Mixer SHALL generate a single output audio file containing the complete mix

### Requirement 7

**User Story:** As a user, I want to preview the generated mix immediately, so that I can hear the result before deciding whether to save it.

#### Acceptance Criteria

1. WHEN the mixing process completes successfully THEN the AI DJ Mixer SHALL automatically load the Mix File into the Audio Player Service
2. WHEN the Mix File is loaded THEN the Audio Player Service SHALL begin playback immediately
3. WHEN the mix is playing THEN the AI DJ Mixer SHALL display playback controls in the Mix Dialog
4. WHEN a user presses the Space key during preview THEN the Audio Player Service SHALL pause or resume playback
5. WHEN a user closes the Mix Dialog during preview THEN the Audio Player Service SHALL stop playback of the Mix File

### Requirement 8

**User Story:** As a user, I want to save the generated mix to a file, so that I can keep mixes I like and play them later.

#### Acceptance Criteria

1. WHEN the mix preview is playing or paused THEN the Mix Dialog SHALL display a "Save Mix" button
2. WHEN a user activates the "Save Mix" button THEN the AI DJ Mixer SHALL prompt for a filename
3. WHEN a user provides a filename THEN the AI DJ Mixer SHALL save the Mix File to the Music Library directory with the specified name
4. WHEN the save operation completes successfully THEN the AI DJ Mixer SHALL display a success notification with the file location
5. IF the save operation fails THEN the AI DJ Mixer SHALL display an error notification with the failure reason

### Requirement 9

**User Story:** As a user, I want to discard a generated mix without saving, so that I can experiment with different mixing instructions without cluttering my library.

#### Acceptance Criteria

1. WHEN the mix preview is playing or paused THEN the Mix Dialog SHALL display a "Discard Mix" button
2. WHEN a user activates the "Discard Mix" button THEN the AI DJ Mixer SHALL stop playback and delete the temporary Mix File
3. WHEN a mix is discarded THEN the Mix Dialog SHALL return to the initial state with track selection and instructions cleared
4. WHEN a user closes the Mix Dialog without saving THEN the AI DJ Mixer SHALL automatically discard the Mix File

### Requirement 10

**User Story:** As a user, I want clear feedback about the mixing process, so that I understand what the system is doing and can troubleshoot issues.

#### Acceptance Criteria

1. WHEN the AI is analyzing instructions THEN the Mix Dialog SHALL display "Analyzing mixing instructions..."
2. WHEN audio processing is occurring THEN the Mix Dialog SHALL display "Processing audio: [operation name]"
3. WHEN the mix is being rendered THEN the Mix Dialog SHALL display "Rendering final mix..."
4. IF any error occurs during mixing THEN the AI DJ Mixer SHALL log the error to the SIGPLAY log file
5. IF any error occurs during mixing THEN the AI DJ Mixer SHALL display a user-friendly error notification with actionable guidance
