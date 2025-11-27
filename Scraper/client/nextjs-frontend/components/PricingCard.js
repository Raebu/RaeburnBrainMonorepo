import React from 'react';

const PricingCard = ({ plan, isFeatured = false, onSelectPlan }) => {
  const {
    name,
    price,
    period, // e.g., "per month"
    description,
    features,
    buttonText = "Get Started",
    buttonVariant = "primary", // 'primary' or 'secondary'
    disabled = false,
  } = plan;

  // Determine button classes based on variant and state
  const getButtonClass = () => {
    if (disabled) {
      return "btn btn-secondary opacity-50 cursor-not-allowed";
    }
    if (buttonVariant === "secondary") {
      return "btn btn-secondary";
    }
    return "btn btn-primary"; // Default to primary
  };

  return (
    <div className={`card flex flex-col h-full ${isFeatured ? 'border-2 border-primary relative' : ''}`}>
      {isFeatured && (
        <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-primary text-on-primary px-4 py-1 text-sm font-medium rounded-full">
          Most Popular
        </div>
      )}
      <div className="p-8 flex-grow flex flex-col">
        <h3 className="text-2xl font-bold mb-2">{name}</h3>
        <div className="mb-4">
          <span className="text-4xl font-bold">{price}</span>
          {period && <span className="text-muted"> / {period}</span>}
        </div>
        <p className="text-muted mb-6 flex-grow">{description}</p>
        <ul className="mb-8 space-y-3 flex-grow">
          {features.map((feature, index) => (
            <li key={index} className="flex items-start">
              <svg className="h-5 w-5 text-primary mr-2 mt-0.5 flex-shrink-0" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span>{feature}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="p-8 pt-0">
        <button
          onClick={() => onSelectPlan && onSelectPlan(plan)}
          disabled={disabled}
          className={getButtonClass()}
          aria-label={`Select ${name} plan`}
        >
          {buttonText}
        </button>
      </div>
    </div>
  );
};

export default PricingCard;
