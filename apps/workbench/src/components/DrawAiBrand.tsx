import drawAiLogo from "/drawai_image.png?inline";

export default function DrawAiBrand() {
  return (
    <div className="brand-row">
      <img className="brand-logo" src={drawAiLogo} alt="" />
      <div className="brand-copy">
        <h1>DrawAI</h1>
      </div>
    </div>
  );
}
