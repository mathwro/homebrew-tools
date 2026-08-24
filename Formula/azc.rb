class Azc < Formula
  desc "Fast subscription context switcher for Azure CLI"
  homepage "https://github.com/mathwro/azc"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/mathwro/azc/releases/download/v0.2.0/azc_0.2.0_darwin_arm64.tar.gz"
      sha256 "29288bbaee28b5979fd79e5df04bb59fab9d47c0fc2917f65a7f9a6eb70542d4"
    end
    on_intel do
      url "https://github.com/mathwro/azc/releases/download/v0.2.0/azc_0.2.0_darwin_amd64.tar.gz"
      sha256 "b1431cb18f848e69a0f35e6e74d360b496775995650a81d9b30e72cf66881481"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/mathwro/azc/releases/download/v0.2.0/azc_0.2.0_linux_arm64.tar.gz"
      sha256 "9078bb2a3cae63d54ce5a86c2e8fb76b1bd9d8e0b3b068bfa5036d592013a0ea"
    end
    on_intel do
      url "https://github.com/mathwro/azc/releases/download/v0.2.0/azc_0.2.0_linux_amd64.tar.gz"
      sha256 "99907c7c4cb070fdaf691f4c49cf21f9f908f87974d111461e4ab72acf18880b"
    end
  end

  def install
    bin.install "azc"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/azc --version")
  end
end
