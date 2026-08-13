class PimManager < Formula
  desc "TUI for activating Microsoft PIM assignments"
  homepage "https://github.com/mathwro/pim-manager"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.1.1/pim-manager_0.1.1_darwin_arm64.tar.gz"
      sha256 "703612ce07cd7dda7656be9047191cc82c96b0a6b833a4cf41cd0d73541d03aa"
    end
    on_intel do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.1.1/pim-manager_0.1.1_darwin_amd64.tar.gz"
      sha256 "29f1e5e537aeefb2e525e894d4cec14cbf0a6086cef9ea6c940d161e70d91a76"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.1.1/pim-manager_0.1.1_linux_arm64.tar.gz"
      sha256 "02d097b0ea445a5634386ff758741f81a9fa19205d5b3965d223fcf2cdf7e4d5"
    end
    on_intel do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.1.1/pim-manager_0.1.1_linux_amd64.tar.gz"
      sha256 "4817d3284661312690835d62ebf822795d86b47f6c1023a64d77c697e62539f3"
    end
  end

  def install
    bin.install "pim-manager"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/pim-manager --version")
  end
end
