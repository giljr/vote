// PollForm Component
const PollForm = () => {
  const [pollTitle, setPollTitle] = React.useState('');
  const [pollOptions, setPollOptions] = React.useState(['', '']);
  const [pollDescription, setPollDescription] = React.useState('');

  const handleTitleChange = (e) => setPollTitle(e.target.value);
  const handleDescriptionChange = (e) => setPollDescription(e.target.value);
  
  const handleOptionChange = (index, value) => {
    const newOptions = [...pollOptions];
    newOptions[index] = value;
    setPollOptions(newOptions);
  };

  const addOption = () => setPollOptions([...pollOptions, '']);
  
  const removeOption = (index) => {
    if (pollOptions.length > 2) {
      setPollOptions(pollOptions.filter((_, i) => i !== index));
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const validOptions = pollOptions.filter(opt => opt.trim() !== '');
    
    if (!pollTitle.trim()) {
      alert('Please enter a poll title');
      return;
    }
    
    if (validOptions.length < 2) {
      alert('Please provide at least 2 options');
      return;
    }

    alert('Poll created!\nTitle: ' + pollTitle + '\nOptions: ' + validOptions.join(', '));
    setPollTitle('');
    setPollOptions(['', '']);
    setPollDescription('');
  };

  return React.createElement('div', { className: 'form_container' },
    React.createElement('div', { className: 'poll-form-section' },
      React.createElement('h2', null, 'Create a New Poll'),
      React.createElement('form', { onSubmit: handleSubmit },
        React.createElement('div', { className: 'form-group' },
          React.createElement('label', { htmlFor: 'pollTitle' }, 'Poll Title'),
          React.createElement('input', {
            id: 'pollTitle',
            type: 'text',
            value: pollTitle,
            onChange: handleTitleChange,
            placeholder: "What's your poll about?",
            className: 'form-input'
          })
        ),
        React.createElement('div', { className: 'form-group' },
          React.createElement('label', { htmlFor: 'pollDescription' }, 'Description (Optional)'),
          React.createElement('textarea', {
            id: 'pollDescription',
            value: pollDescription,
            onChange: handleDescriptionChange,
            placeholder: 'Add more context to your poll...',
            className: 'form-textarea',
            rows: 3
          })
        ),
        React.createElement('div', { className: 'form-group' },
          React.createElement('label', null, 'Poll Options'),
          pollOptions.map((option, index) =>
            React.createElement('div', { key: index, className: 'option-input-group' },
              React.createElement('input', {
                type: 'text',
                value: option,
                onChange: (e) => handleOptionChange(index, e.target.value),
                placeholder: `Option ${index + 1}`,
                className: 'form-input'
              }),
              pollOptions.length > 2 && React.createElement('button', {
                type: 'button',
                onClick: () => removeOption(index),
                className: 'btn-remove',
                title: 'Remove option'
              }, '✕')
            )
          ),
          React.createElement('button', {
            type: 'button',
            onClick: addOption,
            className: 'btn-add-option'
          }, '+ Add Option')
        ),
        React.createElement('button', { type: 'submit', className: 'btn-submit' }, 'Create Poll')
      )
    ),
    React.createElement(LivePreview, {
      title: pollTitle,
      description: pollDescription,
      options: pollOptions
    })
  );
};

// LivePreview Component
const LivePreview = ({ title, description, options }) => {
  const validOptions = options.filter(opt => opt.trim() !== '');
  const hasValidPreview = title.trim() !== '' || validOptions.length > 0;

  return React.createElement('div', { className: 'live-preview-section' },
    React.createElement('h2', null, 'Live Preview'),
    hasValidPreview ?
      React.createElement('div', { className: 'poll-preview' },
        title.trim() && React.createElement('h3', { className: 'preview-title' }, title),
        description.trim() && React.createElement('p', { className: 'preview-description' }, description),
        validOptions.length > 0 && React.createElement('div', { className: 'preview-options' },
          validOptions.map((option, index) =>
            React.createElement('div', { key: index, className: 'preview-option' },
              React.createElement('label', null,
                React.createElement('input', {
                  type: 'radio',
                  name: 'preview-option',
                  disabled: true
                }),
                React.createElement('span', null, option)
              )
            )
          )
        ),
        validOptions.length < 2 && React.createElement('p', { className: 'preview-hint' }, 'Add at least 2 options to preview the full poll')
      ) :
      React.createElement('div', { className: 'preview-placeholder' },
        React.createElement('p', null, 'Start filling out the form to see a preview of your poll here...')
      )
  );
};

// Render when DOM is ready
console.log('poll.js loaded');

function render() {
  console.log('Attempting to render form...');
  const container = document.getElementById('poll-form-root');
  if (!container) {
    console.error('Container not found!');
    return;
  }
  console.log('Container found, creating React root...');
  const root = ReactDOM.createRoot(container);
  root.render(React.createElement(PollForm));
  console.log('Form rendered successfully!');
}

if (document.readyState === 'loading') {
  console.log('DOM still loading, waiting...');
  document.addEventListener('DOMContentLoaded', render);
} else {
  console.log('DOM ready, rendering now...');
  render();
}
