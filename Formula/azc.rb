class Azc < Formula
  desc "Fast subscription context switcher for Azure CLI"
  homepage "https://github.com/mathwro/azc"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/mathwro/azc/releases/download/v0.5.1/azc_0.5.1_darwin_arm64.tar.gz"
      sha256 "c09e1d126e0814b0b85fd1772bce0a2a2ad8fda9d473121fc632cd7aff5a7af1"
    end
    on_intel do
      url "https://github.com/mathwro/azc/releases/download/v0.5.1/azc_0.5.1_darwin_amd64.tar.gz"
      sha256 "2c40db6b2513d554e3627ed2c054daaec4922f3c2ba3c6e0fad6d53643e038bc"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/mathwro/azc/releases/download/v0.5.1/azc_0.5.1_linux_arm64.tar.gz"
      sha256 "662290fbe9a676d6bfb1d507034801e7974713a7d2b485e72fb8e334ee3e4a09"
    end
    on_intel do
      url "https://github.com/mathwro/azc/releases/download/v0.5.1/azc_0.5.1_linux_amd64.tar.gz"
      sha256 "ec4ec0c012d0945e57162a1e3ebcef59b83196ef36e23f1cee2d99cebd808d1a"
    end
  end

  def install
    bin.install "azc"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/azc --version")
  end
end
